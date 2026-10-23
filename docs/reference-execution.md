# Original execution reference — 2026-10-23

실제 a2m 실행으로 ROM 부팅부터 첫 Pascal 실행, 타이틀, Ctrl-U 입력과
유틸리티 메뉴까지 관찰했다. 포팅 코어에서 게임 전체가 실행된다는 뜻은 아니다.
공개 가능한 주소·해시·상태는 `analysis/reference-execution.json`, 원본 메모리,
화면, ROM과 emulator snapshot은 무시되는 `analysis/local/reference/`에 보관한다.

## 실행 환경과 재현

기준은 Apple II Plus / NMOS 6502 / Language Card, a2m 3.0.0이다. 기존 로컬
실행 파일 `../UltimaI_reveng/build/emulator/a2m-socketpair-build/a2m`을 사용했다.
Upstream source는 `d863ad98487639445db16134d260221839cb72e9`이며 기존 로컬
수정은 inherited-fd control transport, raw LF 입력, Apple II 파일 경로 지원이다.
SunDog 분석을 위해 다른 게임의 로직을 가져오거나 이웃 프로젝트를 수정하지 않았다.
실행 파일과 ROM 식별 해시는 각 boot manifest에 기록했다. 이 실행 파일을
배포 앱의 독립적인 게임 코어로 간주하지 않는다.

```sh
python3 tools/reference_runtime.py
python3 tools/reference_runtime.py --sector-image
python3 tools/reference_followup.py analysis/local/reference/20261023-115822
python3 tools/reference_input.py analysis/local/reference/follow-20261023-120102 \
  --checkpoint first-bios-return --turbo max
python3 tools/reference_advance.py analysis/local/reference/input-20261023-122238 --label after-key
python3 tools/export_reference_inventory.py
```

새 실행에서는 출력에 표시된 새 capture 경로를 다음 명령에 전달한다. 각 도구는
기존 evidence 폴더 덮어쓰기를 거부한다. socketpair를 자식 프로세스에 상속하며
TCP listener를 요구하지 않는다. 원본 대신 private copy를 마운트하고 일시정지한
상태에서 쓰기 금지를 설정한다. 종료 시 디스크 해시를 비교한다.
`--sector-image`는 검증된 Utility logical sectors를 a2m이 다시 인코딩하는 비교
실험이다. 원본 WOZ의 비트 타이밍과 동등하다고 간주하지 않는다.

## 관찰된 경계

| 경계 | 실제 관찰과 확인 | 신뢰도·한계 |
|---|---|---|
| `$0801` | ROM이 올린 `$0800..08FF`가 Utility 첫 sector와 일치 | 관찰됨; 해당 ROM/model 범위 |
| `$08FF`, `$4000` | 두 실행 주소 모두 breakpoint 도달 | 관찰됨; 호출 의미 전체를 단일 이름으로 확정하지 않음 |
| `$FEF2`, `$6800` | Language Card 경계와 relocation 후 실행; `$6800` payload 일치 | 관찰됨; 전체 bank trace는 아님 |
| bank 1 `$D293` | 첫 p-code PC `$F248`, mapped segment 0의 3,124 bytes 일치 | 관찰됨 |
| `$FF06` → bank 2 `$D7EF` | 첫 BIOS 서비스 진입, bank 2 코드 bytes 일치 | 관찰됨 |
| 첫 BIOS 복귀 | `$D293`, 다음 p-code PC `$F24E` | 관찰됨 |
| bank 2 `$D6E0` → `$D6E3` | Ctrl-U 후 `LDA $C000` 결과 A=`$95`, 4 cycles | 관찰됨; 입력 시점은 서비스 경계에 맞춤 |
| 이후 실행 | logical-media 경로에서 타이틀 및 유틸리티 메뉴 화면 | 관찰됨; 전체 게임·저장 미검증 |

입력 루틴 `$D6A5`와 latch read `$D6E0`는 Utility T27 / DOS logical sector 3,
각 sector 내 `$A5`, `$E0`에 대응한다. 이미지 offset은 111525와 111584다.
Loader 자체 sector 순서를 적용하여 bytes를 다시 대조했다. 선형 block offset을
DOS image offset으로 그대로 쓰면 틀린 위치가 된다.

REA/Ghidra 12.1.4에 `$D6A5..D7EE`를 명시적으로 매핑해 재분석했다.
Evidence `ev_57c20871b560617e0baefb49f3981d05bdd48c5d0ec71ebaed8b7699ac0d1c4e`
및 전체 assembly/snapshot은 `analysis/local/rea/input-poll-*`에 보관한다.
루틴은 레지스터를 보존하고 `$BF13/BF14`를 증가시키며 `$BF2A`에 따라 입력
경로를 선택한다. 정적 assembly는 장치 실행 관찰을 대신하지 않는다.

## 실패한 시도와 남은 차이

- 첫 capture `20261023-114917`의 frame channel 해석을 잘못했다. 원래 wire는
  little-endian `$AARRGGBB`, 즉 BGRA bytes다. 해당 7개 파생 화면은 비교에서
  제외했고 이후 `.bgra` 원본과 수정된 `.rgba`를 함께 보존한다.
- WOZ continuation `follow-20261023-115323`은 타이틀 그림을 표시하지만 관찰
  종료 시 bank 2 disk 경로에 있었다. logical-media continuation은 안내문과 메뉴까지
  진행했다. 원본 미디어 손상이나 정확한 호환성 원인은 아직 확정하지 않았다.
- 타이틀 뒤 늦은 snapshot의 5초 입력 경계 대기는 timeout이었다. 이를 게임 전체의
  입력 불능으로 일반화하지 않는다. 초기 BIOS 복귀부터 재생하면 경계에 도달한다.
- a2m `key`는 paste 요청이며 **일시정지 상태에서도 실행을 재개한다**. 키를 먼저
  보내고 다음 breakpoint를 설치하면 latch의 high bit가 이미 소모될 수 있었다.
  수정 도구는 `$D6E3` breakpoint를 먼저 설치하고 key를 보내며 별도 run을 하지 않는다.
  이 순서에서 `$95`를 읽는 것을 확인했다. 메모리나 게임 코드는 패치하지 않았다.
- `wait-frame`는 frontend publication 경계다. `max`에서는 수억 cycles가 흐를 수
  있으므로 720이라는 숫자를 실제 Apple II 720 frames나 플레이 시간으로 환산하지 않는다.
- Play Side는 아직 실행 검증하지 않았다. Track 34는 계속 unknown이다.
