# Native input filtering and interpreter hook

SYSTEM.LIBRARY segment 22의 native P2에서 채널 필터와 dispatcher hook을 확인했다.
원본 코드·실제 REA/Ghidra disassembly·기존 Utility 메뉴의 보관 RAM/LC1·선언한 합성 입력을 대조했다.
이 작업에서 새 에뮬레이터 실행이나 앱 코어 연결은 하지 않았다.

## Selector와 버튼 결과

P2는 selector의 low byte를 읽는다. 호출 준비/복귀에서 result word를 남기는 것도
선택된 selector 0..8의 stack fixture로 확인했다.

| Selector | 코드에서 확인한 동작 |
|---|---|
| 0..3 | `$C061 + (selector & 3)` 채널을 읽고 rising edge 반환 |
| 4..7 | 같은 채널의 level 반환; previous 상태는 갱신하지 않음 |
| 정확히 8 | 저장된 `$D004/$D005` dispatch word를 복원하고 false 반환 |

현재 sample과 pending byte를 OR한 bit 7이 `down`이다. Pending에 잡힌 press는
처리 시 소비한다. Edge 모드의 식은 `down & ~previous`이고 previous를 down으로
갱신한다. Level 모드에서는 이 history 갱신을 건너뛴다. Low 7-bit 값만으로는
press가 되지 않는다. 채널의 플랫폼 장치 매핑과 물리 타이밍은 아직 확정하지 않았다.

512개 sample/pending/history/selector 조합, 래치 본문 256개 조합, 설치·복원 2개
사례에서 원본 native 명령과 일치했다. 합성 RAM이 hardware sample 값을 대신한
검증이며 실제 joystick/장치 입력을 실행·측정한 결과는 아니다.

## 게임이 수정하는 p-code dispatcher

보관된 bank-1 상태에서 `$D004/$D005`는 `$A29B`를 가리킨다. 초기 interpreter의
같은 cell은 opcode `$82`인 ADD16의 handler `$D71D`를 가리켰다.
P2의 설치 경로가 이전 word를 저장하고 새 vector를 쓰는 것도 확인했다.

`$A29B`의 hook은 다음 동작을 한다.

1. A와 status를 저장한다.
2. `$C061/$C062` sample을 pending byte 두 개에 각각 OR한다.
3. A와 status를 복원한다.
4. 저장한 원래 ADD16 handler로 JMP한다.

원래 handler 주소는 별도 데이터뿐 아니라 `$A2B1` JMP의 **operand
`$A2B2/$A2B3`**에 들어 있다. 이를 실행 코드와 분리된 data word로 오인하지 않았다.
Selector 8은 원래 dispatch를 복원하지만 이 경로에서 installed flag를 지우지는 않는다.
첫 설치 조건인 `$BF22 & zero-page-$01`의 의미와 소유자는 추가 분석 대상이다.

이는 ADD16 명령을 해석할 때 짧은 입력 pulse를 래치하는 원본 p-system 수정의 구체적
사례다. 전체 입력 sampling 주기나 비용은 아직 측정하지 않았다. 네이티브 포팅의
입력 이벤트 계약을 정하려면 게임 호출 시점·가상 시간과 함께 분석해야 한다.

## 근거와 재현

- Source archive/procedure, Utility track/sector, captured-function hash,
  LC1 hash와 실제 REA ID: `analysis/button-input-evidence.json`.
- 기존 캡처의 native P2 entry `$A208`, hook `$A29B`는 해당 메모리 상태의 주소다.
- `python3 tools/button_input_evidence.py`가 본문과 synthetic checks를 재현한다.
- `sh tools/run_input_analysis.sh`가 별도 native slice만 Ghidra에 import하고
  6개 주석을 저장·readback한다. 원본 파일은 수정하지 않는다.
- 첫 hook slice가 JMP operand 앞에서 끝나 완전한 chain target을 표시하지 못했다.
  그 결과를 보존하고, 3-byte JMP 전체를 포함한 slice로 다시 분석했다.

남은 핵심은 segment 21이 만드는 game event 구조, 키보드 경로, 각 게임 모드에서
이 함수를 호출하는 조건과 입력 횟수·시간의 관계다.
