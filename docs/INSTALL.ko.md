# 설치 안내서

snowsky-melody-peq를 conda 가상환경에서 설치하고 사용하는 방법입니다.

이 라이브러리는 [hidapi](https://github.com/libusb/hidapi)를 사용해 OS의 표준 HID 스택과 직접 통신합니다. 그래서 **별도의 libusb 설치나 Windows Zadig 드라이버 교체가 필요 없습니다.**

## 사전 준비

- **Miniconda** 또는 **Anaconda** ([공식 다운로드](https://docs.conda.io/projects/miniconda/en/latest/))
- **Git**
- **SnowSky Melody** 기기와 USB-C 데이터 케이블

지원 OS: Linux, macOS, Windows 10/11

---

## 1단계 — Conda 가상환경 생성

```bash
conda create -n melody python=3.12 -y
conda activate melody
```

활성화되면 프롬프트 앞에 `(melody)`가 표시됩니다.

---

## 2단계 — 프로젝트 클론 및 설치

```bash
# 원하는 위치로 이동
cd ~/projects     # 예시

# 클론
git clone https://github.com/dialektike/snowsky-melody-peq.git
cd snowsky-melody-peq

# 편집 가능 모드(-e)로 설치 — hidapi가 함께 자동 설치됨
pip install -e .
```

설치 확인:

```bash
(melody) $ melody-peq --version
melody-peq 0.1.0
```

> **참고**: 대부분의 환경에서 hidapi는 wheel(미리 컴파일된 바이너리)로 설치되므로 추가 작업이 필요 없습니다. 만약 wheel이 없는 환경(예: 일부 ARM Linux)에서 pip install이 실패하면 빌드 도구가 필요할 수 있습니다 — 아래 트러블슈팅 참조.

---

## 3단계 — Linux 전용: udev 규칙

Linux에서 sudo 없이 HID 기기에 접근하려면 udev 규칙이 필요합니다. **macOS와 Windows는 이 단계를 건너뛰세요** — OS가 알아서 권한을 부여합니다.

```bash
sudo cp udev/99-fiio.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

규칙 적용 후 **Melody를 USB에서 뺐다가 다시 꽂아야** 새 권한이 적용됩니다.

---

## 4단계 — 설치 확인

Melody를 USB로 연결한 상태에서:

```bash
melody-peq dump
```

다음과 같은 출력이 나오면 성공입니다 (밴드 수치는 디바이스 상태에 따라 다름):

```
Device  : SNOWSKY Melody
EQ on   : unknown (no response)
Preset  : 0
Pre-amp : -3.0 dB
Bands   : 10

  Band 0: 30Hz +3.5dB Q=0.61 LOW_SHELF
  Band 1: 52Hz +1.2dB Q=1.89 PEAK
  ...
  Band 9: 3735Hz +1.8dB Q=0.70 HIGH_SHELF
```

> **출력에 대해 알아둘 점**
>
> - `EQ on : unknown (no response)`는 정상입니다. Melody는 `EQ_SWITCH` 쿼리에 응답하지 않는 펌웨어 특성을 가지고 있어서 라이브러리가 EQ on/off 상태를 알 수 없음을 정직하게 표시합니다.
> - `Preset` 값은 디바이스의 "Personal / Modified" 인디케이터입니다 (실기 검증 결과):
>   - 웹에서 프리셋 타일을 클릭한 직후에만 정확한 ID 반환 (Jazz=`0`, Pop=`1`, ..., HIFIMAN=`7`, FT5=`8`, FH3=`9`, bypass=`240`)
>   - 라이브 EQ가 어떤 식으로든 수정된 상태(웹의 Personal 탭이거나, 이 라이브러리로 `set_preset()`/`set_band()` 호출한 상태)에서는 `0` 반환
>   - 라이브러리에서 활성 슬롯을 알아야 한다면 직접 추적해야 합니다 — 자세한 내용은 `docs/PROTOCOL.md` 참조
> - `Bands : 10`은 정상입니다 (Melody는 10밴드 PEQ).

---

## 환경 관리

### 작업 시작할 때마다

```bash
conda activate melody
cd ~/projects/snowsky-melody-peq
```

### 작업 끝낼 때

```bash
conda deactivate
```

### 환경 삭제 (완전 제거)

```bash
conda deactivate
conda env remove -n melody
```

### 환경 정보 확인

```bash
conda env list                    # 모든 환경 목록
conda list -n melody              # melody 환경에 설치된 패키지
```

---

## 트러블슈팅

### `melody-peq: command not found`

`conda activate melody`를 깜빡했을 가능성:
```bash
which melody-peq
# 출력에 melody 환경 경로가 포함되어야 함
```

### `No FiiO HID device found (VID=0x2972)`

- USB 케이블이 데이터 지원인지 확인 (충전 전용 케이블은 불가)
- Melody 본체에서 USB DAC 모드가 켜져 있는지 확인
- OS가 인식하는지 확인:
  - **Linux**: `lsusb | grep 2972`
  - **macOS**: `system_profiler SPUSBDataType | grep -i melody`
  - **Windows**: 장치 관리자에서 "SnowSky Melody" 확인

### `Permission denied` 또는 `Failed to open Melody HID device` (Linux)

udev 규칙이 적용 안 됐거나 Melody를 재연결 안 한 경우:
```bash
ls -la /etc/udev/rules.d/99-fiio.rules     # 파일 존재 확인
cat /etc/udev/rules.d/99-fiio.rules        # 내용 확인
sudo udevadm control --reload-rules && sudo udevadm trigger
# Melody 재연결
```

권한 확인용 임시 우회:
```bash
sudo $(which python) -m snowsky_melody_peq.cli dump
```

### `Failed to open Melody HID device` (Windows)

다른 앱이 Melody를 점유 중일 가능성:
- **FiiO Control 데스크톱 앱**을 닫고 다시 시도
- 브라우저의 `fiiocontrol.fiio.com` 탭이 열려 있으면 닫기

### `NotAMelodyError: Connected FiiO device(s) are not a SnowSky Melody`

USB 제품 문자열에 "melody"가 포함되지 않은 경우. 실제 문자열 확인:
```bash
python -c "
import hid
for info in hid.enumerate(0x2972, 0):
    print(info.get('product_string'), '|', info.get('manufacturer_string'))
"
```

출력된 제품 문자열을 알려주시면 식별 키워드를 보강하겠습니다.

### `ImportError: No module named 'hid'` 또는 hidapi 빌드 실패 (드물게 ARM Linux 등)

미리 컴파일된 wheel이 없는 환경에서 발생. 시스템 의존성 설치:

**Ubuntu/Debian:**
```bash
sudo apt-get install -y libudev-dev libusb-1.0-0-dev python3-dev
pip install --force-reinstall hidapi
```

**Fedora/RHEL:**
```bash
sudo dnf install -y systemd-devel libusbx-devel python3-devel
pip install --force-reinstall hidapi
```

### conda 환경 안에서 시스템 Python이 실행됨

가끔 환경이 제대로 활성화 안 되는 경우:
```bash
conda init bash             # 셸 종류에 맞게 (zsh, fish 등)
# 새 터미널 열기
conda activate melody
which python                # 환경 경로가 출력돼야 함
```

---

## 다음 단계

설치 검증이 끝나면 다음 문서를 참고하세요:

- 사용법과 API: 프로젝트 루트의 [`README.md`](../README.md)
- 프로토콜 상세: [`docs/PROTOCOL.md`](PROTOCOL.md)
- 예제 코드: [`examples/`](../examples/) 디렉토리

자주 쓰는 명령어 요약:

```bash
melody-peq dump                              # 현재 EQ 상태 출력
melody-peq apply profile.txt --slot 1        # AutoEQ 파일 적용 후 USER1에 저장
melody-peq preset 7                          # USER1로 전환 (8=USER2, 9=USER3)
melody-peq preset 240                        # EQ bypass (Melody의 "Close EQ")
melody-peq reset                             # 현재 슬롯 초기화
```
