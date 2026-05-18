# 하드웨어 검증 가이드

실제 SnowSky Melody 기기와 `examples/hardware_test.py`, FiiO 공식 웹 UI를 함께 사용해 라이브러리의 SET 경로를 시각적으로 검증하는 방법입니다.

> **English**: [`HARDWARE_TESTING.md`](HARDWARE_TESTING.md)

## 왜 시각 검증인가

Melody는 일부 명령에서:

- 응답이 아예 없습니다 (`get_eq_enabled()`가 `None` 반환).
- 기대와 다른 부작용을 보입니다 (예: `set_preset(160)`이 USER 슬롯 전환 대신 bypass로 떨어짐).
- 신뢰할 수 있는 ACK가 없습니다.

FiiO 웹 UI에서 직접 보면 readback 한계를 우회할 수 있습니다 — 브라우저에 디바이스의 실제 상태가 표시되기 때문입니다.

## 사전 준비

- USB로 연결되고 웹 UI에서 동작하는 SnowSky Melody.
- 가상환경에 설치된 라이브러리 ([`README.ko.md`](../README.ko.md) 참고).
- WebHID를 지원하는 Chromium 계열 브라우저 (Chrome, Edge, Brave 등).
- FiiO Melody 컨트롤 웹 페이지가 열려 있는 탭. (FiiO 제품 페이지에서 정확한 URL을 확인하세요.)

## connect–disconnect 댄스

USB HID는 한 번에 하나의 앱만 디바이스를 점유할 수 있습니다. Python과 브라우저를 번갈아 가며 작업합니다:

```
┌──────────────┐  Python이 SET 하나 실행 후 디바이스 close
│   Python     │ ─────────────────────────────────────►
│              │
└──────────────┘                                       ┌──────────────┐
                                                       │   Web UI     │
       ◄──────────────────────── Refresh 클릭, 시각 확인
                                                       │              │
                                                       └──────────────┘
       ◄──────────────────────── Disconnect 클릭

┌──────────────┐  Python이 다음 테스트 실행
│   Python     │ ─────────────────────────────────────►
```

`examples/hardware_test.py`가 Python 쪽을 자동화합니다: 모든 테스트 동작이 디바이스를 열고, 한 작업을 수행한 뒤, 즉시 닫아서 웹이 점유할 수 있게 합니다.

## `hardware_test.py` 실행

```bash
python examples/hardware_test.py
```

다음과 같은 메뉴가 표시됩니다:

```
SnowSky Melody hardware test helper
Results will append to /…/melody-test-log.txt

Available tests:
   1. dump current state (read-only)
   2. probe preset names 0..10 + 160..162 + 240 (map USER slots)
   3. set_preset(7) — probe likely USER1 ID on Melody
   …
   q. quit

Select test:
```

각 테스트마다:

1. 테스트 번호 입력 후 Enter.
2. 스크립트가 디바이스를 열어 동작을 실행하고
   `device closed. Switch to the FiiO web UI and connect.` 메시지 출력.
3. 브라우저에서 FiiO 웹 UI의 **Connect** 클릭. 표시 상태가 오래된 것 같으면 **Refresh** 클릭. 테스트가 한 동작과 UI에 보이는 상태를 비교.
4. 터미널로 돌아와 결과 입력:
   ```
   result [pass/fail/skip + optional note]:
   ```
   예: `pass: HIFIMAN 슬롯이 빨간색으로 활성화됨`. 입력 내용은 타임스탬프와 함께 `melody-test-log.txt`에 추가됩니다.
5. 다음 테스트 전에 웹 UI에서 **Disconnect** 클릭해서 Python이 다시 디바이스를 잡을 수 있게 합니다.

## 권장 순서

처음 검증 시 아래 순서로. 앞쪽은 읽기 전용이거나 쉽게 되돌릴 수 있고, 뒤쪽일수록 파괴적입니다.

1. **테스트 1 — dump 현재 상태.** 디바이스 접근 가능 여부 확인 + 시작 EQ 캡처. 백업이 필요하면 파일로 저장: `melody-peq dump > ~/melody-pre-test.txt`.
2. **테스트 2 — preset 이름 매핑.** 가장 정보가 많은 단일 테스트입니다. `get_preset_name()`을 모든 후보 ID에 대해 한 번에 읽어옵니다. 웹에서 설정한 이름(`HIFIMAN`, `FT5...`, `FH3` 등)을 반환하는 ID가 실제 USER 슬롯입니다.
3. **테스트 3, 4, 5 — `set_preset(7|8|9)`.** 웹 UI 타일 배치가 시사하는 대로, 낮은 번호 ID가 실제로 활성 프리셋을 전환하는지 확인.
4. **테스트 9, 10 — `set_preset(160)` / `set_user_slot(1)`.** K13 R2R 프로토콜 문서의 USER 슬롯 ID(160-162)가 Melody에서 동작하는지, 아니면 bypass로 떨어지는지.
5. **테스트 8 — `set_preset(240)`.** Bypass 메커니즘 확인. 웹 UI의 **Close EQ**가 강조되어야 합니다.
6. **테스트 6, 7 — `set_eq_enabled(False)` / `(True)`.** 응답 없는 `EQ_SWITCH` SET이 실제로 디바이스 상태를 변경하는지 검증.
7. **테스트 11, 12 — `set_preamp`.** 웹 슬라이더가 움직여야 합니다.
8. **테스트 13 — `set_band(0, 30 Hz, +12 dB, …)`.** 극단적 low-shelf 부스트. 웹에서 Band 0이 +12 dB로 점프해야 합니다. 음악 재생 중이면 청각으로도 확인 가능.
9. **테스트 14 — `save_to_user(1)`.** USER1에 현재 EQ 영구 저장. 아래 재부팅 테스트와 함께 진행.
10. **재부팅 지속성 (수동).** Melody USB 분리 → 10초 대기 → 재연결 → 테스트 1 다시 실행. USER1 내용이 보존되어 있는지 확인.
11. **테스트 16 — `reset_eq()`.** 파괴적. 활성 슬롯을 평탄화합니다. 가장 마지막에 실행하세요 — 이후에는 다시 튜닝해야 합니다.

## 결과 보고

세션이 끝나면 세 곳에 노트가 도움 됩니다:

- **`melody-test-log.txt`** — 자동 기록됨, 별도 작업 불필요.
- **`docs/PROTOCOL.md` "Melody-specific notes"** — 새로 확인된 매핑을 PR로 추가 (예: "USER 슬롯은 7-9에 있고, 160-162가 아니다").
- **`CHANGELOG.md`** — "Verified on" / "Known limitations" 항목 갱신.

테스트 결과가 라이브러리의 현재 동작과 모순되면 그것은 버그입니다 — 관련 로그와 (해당하면) 웹 UI 스크린샷과 함께 이슈를 열어 주세요.

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `No FiiO HID device found` | Melody 분리됨, 또는 웹이 점유 중 | 재연결, 웹 탭에서 Disconnect 클릭 |
| Linux에서 `Failed to open Melody HID device` | udev 규칙 누락 | [`INSTALL.ko.md`](INSTALL.ko.md) 3단계 참고 |
| SET 이후 웹 UI가 이전 상태 표시 | 브라우저가 이전 read를 캐시 | 웹 UI에서 **Refresh** 클릭 |
| 웹 UI의 **Connect** 버튼이 반응 없음 | Python이 디바이스 점유 중이거나 브라우저의 WebHID 권한 분실 | Python 종료 (또는 `device closed.` 줄 출력 대기); 필요하면 주소창 자물쇠 아이콘에서 권한 재허가 |
| `set_preset(N)` 이후에도 활성 프리셋 타일이 그대로 | `N`이 Melody의 유효 프리셋이 아니어서 bypass로 떨어졌을 가능성 | 다른 후보 ID 시도; **Close EQ** 강조 상태 확인 |
