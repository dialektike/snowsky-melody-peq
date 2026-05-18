# 하드웨어 검증 가이드

실제 SnowSky Melody 기기와 `examples/hardware_test.py`, FiiO 공식 웹 UI를 함께 사용해 라이브러리 동작을 시각적으로 검증하는 방법입니다.

> **English**: [`HARDWARE_TESTING.md`](HARDWARE_TESTING.md)

존재 이유 두 가지:

- Melody는 일부 명령(`EQ_SWITCH`)에 응답하지 않아서 read-back만으로는 "SET이 실제로 동작했나"를 알 수 없습니다. 웹 UI가 진실의 출처입니다.
- 라이브러리는 한 maintainer의 실기에서 도출된 Melody 고유 동작(USER 슬롯 활성화 ID `7..9`, `save_to_user` 활성화 ID 변환 등 — [`PROTOCOL.md`](PROTOCOL.md) 참고)을 코드에 반영해 두었는데, 다른 기기는 다를 수 있습니다. 이 가이드는 그것까지 확인하는 방법입니다.

## 이미 검증된 사실 (재발견 불필요)

다음은 macOS + hidapi 0.15.0 + 한 대의 SnowSky Melody에서 검증된 사실입니다. 테스트 전에 한 번 훑어 보세요:

- 10개 PEQ 밴드. `get_band_count()`로 확인됨.
- USER 슬롯 활성화 ID: `7` (USER1), `8` (USER2), `9` (USER3). K13의 `160..162`를 보내면 디바이스가 bypass로 떨어집니다.
- 공장 프리셋 ID: `0` Jazz, `1` Pop, `2` Rock, `3` Dance, `4` R&B, `5` Classic, `6` Hip-Pop.
- 명시적 bypass: `set_preset(240)` → 웹 UI에서 **Close EQ** 강조됨.
- `EQ_SWITCH` (0x1A)는 Melody가 무시. `get_eq_enabled()`는 `None` 반환, `set_eq_enabled()`는 readback 검증 불가.
- `save_to_user(slot)`은 활성화 ID 전송 방식으로 end-to-end 검증됨 (USB 전원 분리 후에도 EEPROM 보존).
- `get_preset()`은 "Personal / Modified" 인디케이터입니다: 웹에서 타일을 클릭한 직후에만 정확한 ID 반환. 프로그래밍 방식 `set_preset()`/`set_band()` 호출 후에는 `0` 반환. 시나리오별 동작 표는 [`PROTOCOL.md`](PROTOCOL.md) 참고.

## 왜 시각 검증인가

Melody는 일부 명령에서:

- 응답이 아예 없습니다 (`get_eq_enabled()`가 `None` 반환).
- 와이어로 echo 없이 내부 상태를 변경합니다 (예: `set_preset()`).
- read-back 쿼리로는 노출되지 않는 별도 펌웨어 인디케이터("active tile" vs "live bands")가 있습니다.

FiiO 웹 UI에서 직접 보면 이 모든 한계를 우회할 수 있습니다.

## 사전 준비

- USB로 연결되고 웹 UI에서 동작하는 SnowSky Melody.
- 가상환경에 설치된 라이브러리 ([`README.ko.md`](../README.ko.md) 참고).
- WebHID를 지원하는 Chromium 계열 브라우저 (Chrome, Edge, Brave 등).
- FiiO Melody 컨트롤 웹 페이지가 열려 있는 탭.

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

라이브러리는 이미 하드웨어 검증을 마쳤습니다. 이 순서는 본인 기기에서도 동일한 결과가 나오는지 가장 효율적으로 확인하는 흐름입니다. 앞쪽은 읽기 전용, 뒤쪽일수록 파괴적입니다.

1. **테스트 1 — dump 현재 상태.** 디바이스 접근 가능 여부 확인. `EQ enabled`는 `unknown (no response)`로 표시되어야 정상. 백업이 필요하면 파일로 저장: `melody-peq dump > ~/melody-pre-test.txt`.
2. **테스트 2 — preset 이름 매핑.** `160`/`161`/`162`에서 USER 슬롯 이름이 반환되고, `0..10`은 garbage placeholder가 와야 정상. USER 슬롯 이름이 `160..162` 외의 ID에서 나오면 라이브러리의 `get_user_slot_name()` 매핑이 본인 기기에는 안 맞는 것 — 이슈를 열어 주세요.
3. **테스트 3, 4, 5 — `set_preset(7|8|9)`.** 웹 UI에서 HIFIMAN, FT5, FH3 (또는 본인 USER 슬롯 이름)가 강조되어야 합니다. **Close EQ**가 강조되면 활성화 ID 매핑이 본인 기기에서는 다른 것입니다.
4. **테스트 8 — `set_preset(240)`.** 웹 UI에서 **Close EQ**가 (테두리뿐이 아니라) 단색 빨강으로 강조되어야 합니다.
5. **테스트 9, 10 — `set_preset(160)` / `set_user_slot(1)`.** 예상 동작: `set_user_slot`은 내부에서 `set_preset(7)`로 변환되므로 USER1 활성화, raw `set_preset(160)`은 bypass로 떨어짐.
6. **테스트 6, 7 — `set_eq_enabled(False)` / `(True)`.** 웹 변화 없음이 예상. Melody가 `EQ_SWITCH`를 무시함을 재확인.
7. **테스트 11, 12 — `set_preamp`.** 웹 슬라이더가 움직여야 합니다.
8. **테스트 13 — `set_band(0, 30 Hz, +12 dB, …)`.** 웹 Home 탭: Band 1이 30 Hz, +12 dB, Q=0.70, LS로 변경되어야 합니다. 음악 재생 중이면 청각으로도 확인 가능.
9. **테스트 14 — `save_to_user(1)`.** 현재 라이브 EQ를 USER1에 영구 저장 (HIFIMAN 덮어씀 — 잃어도 되는 슬롯인지 확인). 그 후 테스트 4 (`set_preset(8)`), 테스트 3 (`set_preset(7)`), 테스트 1을 차례로 실행 — Band 0이 여전히 변경된 값이면 EEPROM 슬롯 재로드 정상.
10. **재부팅 지속성 (수동).** Melody USB 분리 → 10초 대기 → 재연결 → 테스트 1 다시 실행. save_to_user 수정값이 여전히 유지되어야 합니다. 가장 강력한 정확성 신호입니다.
11. **테스트 16 — `reset_eq()`.** 파괴적. 활성 슬롯을 평탄화합니다. 가장 마지막에 실행하세요 — 이후에는 다시 튜닝해야 합니다.

## 결과 보고

세션이 끝나면:

- **`melody-test-log.txt`** — 자동 기록됨. 이슈/PR 열 때 첨부해 주세요.
- **`docs/PROTOCOL.md` "Melody-specific notes"** — 이미 문서화된 것과 다른 매핑을 발견하면 PR로 추가.
- **`CHANGELOG.md`** — 본인 기기에서 기존 사실이 재확인되면 "Verified on"에, 새 발견이면 "Known limitations"에 기록.

테스트 결과가 라이브러리의 현재 동작과 모순되면 그것은 버그입니다 — 관련 로그와 웹 UI 스크린샷과 함께 이슈를 열어 주세요.

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `No FiiO HID device found` | Melody 분리됨, 또는 웹이 점유 중 | 재연결, 웹 탭에서 Disconnect 클릭 |
| Linux에서 `Failed to open Melody HID device` | udev 규칙 누락 | [`INSTALL.ko.md`](INSTALL.ko.md) 3단계 참고 |
| SET 이후 웹 UI가 이전 상태 표시 | 브라우저가 이전 read를 캐시 | 웹 UI에서 **Refresh** 클릭 |
| 웹 UI의 **Connect** 버튼이 반응 없음 | Python이 디바이스 점유 중이거나 브라우저의 WebHID 권한 분실 | Python 종료 (또는 `device closed.` 줄 출력 대기); 필요하면 주소창 자물쇠 아이콘에서 권한 재허가 |
| `set_preset(7)` 했는데 `active preset: 0` 표시 | 정상 — `get_preset()`은 프로그래밍 SET 직후 0("Personal/Modified")으로 돌아갑니다. 밴드 자체는 정확히 로드됨 | `Band 0..9` 출력을 기대 슬롯 내용과 비교해서 확인 |
| `set_preset(N)`에서 웹의 **Close EQ**가 강조됨 | `N`이 Melody의 유효 활성화 ID가 아님 → 펌웨어가 bypass로 처리 | ID `0..9` 또는 `240`만 사용 |
