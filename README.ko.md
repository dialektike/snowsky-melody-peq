# snowsky-melody-peq

**FiiO SnowSky Melody**의 파라메트릭 EQ를 USB HID로 제어하는 Python 라이브러리입니다.

> **English README**: [`README.md`](README.md)

> **고지.** 본 프로젝트는 비공식 개인 프로젝트입니다. Guangzhou FiiO Electronics Technology Co., Ltd.와 어떠한 제휴, 보증, 후원 관계도 없습니다. "FiiO"와 "SnowSky"는 해당 권리자의 상표이며, 여기서는 기기 호환성 표시 목적으로만 사용합니다.

안드로이드 폰이나 브라우저 없이 Python 스크립트나 셸에서 Melody의 PEQ를 설정할 수 있습니다. 라이브러리는 SnowSky Melody 외의 USB 기기는 절대 건드리지 않으므로 다른 DAC을 함께 연결한 상태에서도 안전하게 실행 가능합니다.

## 할 수 있는 일

- Melody의 모든 PEQ 밴드(주파수, 게인, Q, 필터 타입) 읽기/쓰기.
- 글로벌 프리앰프 조정.
- USER 프리셋 슬롯(USER1..USER3) 전환과 EQ 영구 저장.
- [AutoEq](https://github.com/jaakkopasanen/AutoEq) 커뮤니티 튜닝 프로파일 가져오기.
- CLI: `melody-peq dump | apply | preset | reset`.

## 할 수 없는 일

- 다른 FiiO 기기는 제어하지 않습니다. K13이나 BTR17 같은 다른 기기를 연결하면 `NotAMelodyError`를 던지고 깨끗하게 종료합니다.
- EQ 외 Melody 설정(SPDIF 토글, DAC 필터, 펌웨어 업데이트)은 변경하지 않습니다. 이런 기능은 FiiO Control 안드로이드 앱을 이용하세요.
- 오디오 I/O는 처리하지 않습니다. 컨트롤 전용 라이브러리입니다.

## 설치

> 단계별 conda 기준 상세 설치 가이드는 [`docs/INSTALL.ko.md`](docs/INSTALL.ko.md)를 참고하세요.

`hidapi` 등 의존성이 시스템 Python과 충돌하지 않도록 가상환경에 격리해서 설치하시기를 권장합니다.

**conda 사용** (이미 사용 중이라면 권장):

```bash
conda create -n melody python=3.12 -y
conda activate melody

git clone https://github.com/dialektike/snowsky-melody-peq
cd snowsky-melody-peq
pip install -e .
```

**venv 사용** (Python 표준 라이브러리, 추가 도구 없이):

```bash
git clone https://github.com/dialektike/snowsky-melody-peq
cd snowsky-melody-peq

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
```

확인:

```bash
melody-peq --version
```

macOS와 Windows는 이것으로 끝입니다. 라이브러리는 [hidapi](https://github.com/libusb/hidapi)를 사용하므로 OS의 네이티브 HID 스택과 직접 통신합니다 — `libusb`도, Zadig 드라이버 교체도 필요 없습니다. 새 셸에서는 매번 `conda activate melody` (또는 `source .venv/bin/activate`) 해주어야 `melody-peq` 명령어가 PATH에 잡힙니다.

### Linux: sudo 없이 기기 접근하기 위한 udev 규칙

```bash
sudo cp udev/99-fiio.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

규칙 설치 후 Melody를 USB에서 뺐다가 다시 꽂아야 합니다.

## 빠른 시작

```python
from snowsky_melody_peq import MelodyPEQ, FilterType

with MelodyPEQ() as dev:
    print(f"Device: {dev.name}, {dev.get_band_count()} bands")

    dev.set_user_slot(1)             # USER1로 전환
    dev.set_preamp(-3.0)
    dev.set_band(0, freq=80,   gain=+4.0, q=0.71, filter_type=FilterType.LOW_SHELF)
    dev.set_band(1, freq=2500, gain=-3.5, q=1.41, filter_type=FilterType.PEAK)
    dev.save_to_user(slot=1)         # USER1에 영구 저장
```

AutoEQ 프로파일 적용:

```python
from snowsky_melody_peq import MelodyPEQ, parse_autoeq_file

preamp, bands = parse_autoeq_file("HE-X4_ParametricEQ.txt")
with MelodyPEQ() as dev:
    written, count = dev.apply_profile(preamp, bands, slot=1)
    print(f"USER1에 {written}/{count} 밴드 기록")
```

`parse_autoeq_file()`은 파일을 읽으며 경로가 잘못되면 `FileNotFoundError`를
던집니다. `parse_autoeq()`는 파일의 *내용*을 문자열로 받습니다 (`str`은
절대 경로로 해석되지 않습니다). `apply_profile()`은 프로파일을 기기 밴드
수에 맞게 자르고, 남는 밴드를 플랫(0 dB)으로 채워 슬롯에 이전에 저장돼
있던 EQ가 새 프로파일 밑에 남지 않도록 한 뒤, 영구 저장까지 수행합니다.

셸에서:

```bash
melody-peq dump
melody-peq apply HE-X4_ParametricEQ.txt --slot 1
melody-peq preset 7              # USER1로 전환
melody-peq preset 240             # EQ bypass
```

더 많은 예제는 [`examples/`](examples/)를 참고하세요.

## MCP 서버 (Claude / Anthropic tool calling)

선택적 MCP 서버가 동일 패키지에 포함되어 있어 Claude Desktop, Claude Code, 그 외 MCP 클라이언트에서 Melody의 EQ를 tool로 읽고 쓸 수 있습니다.

extra 설치:

```bash
pip install -e ".[mcp]"      # 본 체크아웃 내, 또는
pip install snowsky-melody-peq[mcp]
```

이로써 `mcp-snowsky-melody` 콘솔 스크립트가 등록됩니다. 절대 경로 확인:

```bash
which mcp-snowsky-melody
```

MCP 클라이언트에 등록합니다. Claude Desktop의 경우 `claude_desktop_config.json`에 추가:

```json
{
  "mcpServers": {
    "snowsky-melody": {
      "command": "/절대/경로/mcp-snowsky-melody"
    }
  }
}
```

Claude Code의 경우:

```bash
claude mcp add snowsky-melody -- /절대/경로/mcp-snowsky-melody
```

전체 tool 레퍼런스: [`docs/MCP_TOOLS.md`](docs/MCP_TOOLS.md).

## API 한눈에 보기

| 메서드 | 용도 |
|---|---|
| `get_band_count() / get_eq_enabled() / get_preset() / get_preamp()` | 상태 읽기 — `T \| None` 반환 (`None` = 기기 무응답) |
| `get_band(i) / get_all_bands()` | PEQ 밴드 읽기 |
| `get_preset_name(i) / get_user_slot_name(1..3)` | 프리셋/슬롯에 저장된 이름 읽기 |
| `set_eq_enabled(on)` *(Melody에서 무동작 — quirks 참조)* / `set_user_slot(1..3) / set_preset(id) / set_preamp(db)` | 상태 설정 |
| `set_band(i, freq, gain, q, filter_type) / set_bands(list)` | PEQ 쓰기 |
| `apply_profile(preamp, bands, slot)` | 프로파일 일괄 적용: 기기 밴드 수로 자르고, 남는 밴드를 플랫으로 채운 뒤 슬롯에 영구 저장 |
| `save_to_user(slot) / reset_eq()` | 영구 저장(슬롯 1-3) 또는 초기화 |

모듈 수준 헬퍼: `parse_autoeq(text_or_path)`는 AutoEQ ParametricEQ 내용을
파싱합니다 (`str` = 내용 그대로, `Path` = 파일). `parse_autoeq_file(path)`는
파일을 읽으며 경로가 없으면 즉시 예외를 던집니다. `OFF` 필터 줄은
건너뛰고, 남은 밴드는 0부터 순차 인덱스를 다시 부여합니다.

`FilterType` 값: `PEAK`, `LOW_SHELF`, `HIGH_SHELF`, `BAND_PASS`, `LOW_PASS`, `HIGH_PASS`, `ALL_PASS`.

`Band`는 생성 시점에 인자 범위를 검증합니다: `freq` 20–20000 Hz, `gain` ±24 dB, `Q` 0.01–100. 범위를 벗어나면 `ValueError`를 던지며, `set_band()`도 와이어에 쓰기 전에 동일한 검증을 수행합니다. 반대로 읽기 경로는 의도적으로 관대합니다: `get_band()` / `get_all_bands()`는 기기가 보고한 값을 범위 밖이라도 그대로 반환합니다 (초기화 직후 밴드는 `freq=0`을 보고할 수 있습니다).

Melody는 USER 슬롯 1–3을 제공합니다. **활성화 ID는 `7..9`입니다** (K13 R2R 문서의 `160..162`가 아닙니다 — 그 값들을 Melody에 보내면 bypass로 떨어집니다). 프리셋 ID `240`은 명시적 bypass. 공장 프리셋은 `0..6` (Jazz, Pop, Rock, Dance, R&B, Classic, Hip-Pop)이고 읽기 전용입니다.

`set_user_slot(1..3)`과 `save_to_user(1..3)`은 1/2/3 슬롯 번호를 받고, 라이브러리가 내부적으로 올바른 활성화 ID로 변환합니다. `get_user_slot_name(1..3)`은 저장된 슬롯 이름을 조회합니다 (디바이스가 별도의 레거시 ID 체계로 보관 — `docs/PROTOCOL.md` 참고).

### Melody 고유 특성 (실기 확인)

- Melody는 **`EQ_SWITCH` (CMD `0x1A`)에 응답하지 않습니다.** 그래서 Melody에서는 `get_eq_enabled()`가 `None`을 반환합니다. 의도된 bypass 경로는 `set_preset(240)`입니다. 전체 특성 목록은 `docs/PROTOCOL.md`를 보세요.
- Melody는 **10개 PEQ 밴드**를 가집니다.
- 프리셋 ID는 이중 체계를 사용합니다: 활성화는 순차 `0..9` + `240`, 슬롯 이름 저장소는 레거시 `160..162` 주소에 있습니다.
- `get_preset()`은 "현재 활성 슬롯" 쿼리가 아니라 **"Personal / Modified" 인디케이터**입니다 — 웹 UI에서 타일을 클릭한 직후에만 정확한 ID 반환, 그 외 프로그래밍 방식 `set_preset()`/`set_band()` 호출 후에는 `0` 반환. 밴드 자체(`get_all_bands()`)는 항상 정확합니다. 활성 슬롯은 애플리케이션이 직접 추적하세요.
- `save_to_user(slot=1..3)`은 USB 전원 분리 후에도 유지됩니다 (EEPROM 영구 저장 end-to-end 검증 완료).

## 동작 원리

라이브러리는 FiiO Control 안드로이드 앱/웹 인터페이스와 동일한 패킷 포맷을 사용해 USB HID 인터페이스 3을 통해 Melody와 통신합니다:

```
GET: [0xBB, 0x0B, 0x00, 0x00, CMD, LEN, ...DATA, 0x00, 0xEE]
SET: [0xAA, 0x0A, 0x00, 0x00, CMD, LEN, ...DATA, 0x00, 0xEE]
```

전체 EQ 명령어 집합과 필드 인코딩은 [`docs/PROTOCOL.md`](docs/PROTOCOL.md)에 문서화되어 있습니다.

## 안전성

이 라이브러리는 **오직** EQ 명령 코드(`0x15`–`0x1B`, `0x30`)만 탑재합니다. 임의 명령 코드를 구현하거나 노출하거나 받지 않으므로 펌웨어 업데이트나 공장 초기화 명령을 실수로 보낼 수 없습니다. 연결 시 Melody-only 식별 체크가 두 번째 안전 계층입니다: 다른 FiiO 기기가 함께 연결되어 있어도 그것들은 건드리지 않습니다.

## 크레딧

- [SmookeyDev/fiio-k13-control](https://github.com/SmookeyDev/fiio-k13-control) — FiiO Control APK v4.0.3의 원본 역공학 작업. K13 R2R과 Melody가 EQ 명령 공간을 공유하므로 해당 작업에서 도출된 프로토콜 문서가 본 프로젝트에도 적용됩니다.
- [AutoEq](https://github.com/jaakkopasanen/AutoEq) — 커뮤니티 튜닝 헤드폰 PEQ 데이터베이스.
- [hidapi](https://github.com/libusb/hidapi) — 크로스 플랫폼 HID 라이브러리.

## 라이선스

MIT — [LICENSE](LICENSE) 참조.
