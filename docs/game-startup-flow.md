# Original game startup and state dispatch

Play SYSTEM.STARTUP segment 1의 6개 procedure는 이제 명령 길이의 미확인 경계 없이
정적으로 연결된다. External call과 서비스의 **정상 복귀를 조건으로 한 CFG**이며,
디스크 I/O·장면 실행 전체를 관찰했다는 뜻은 아니다.

## 복원한 초기화 순서

P1의 entry jump를 따라가면 다음 순서다. 숫자는 segment operand이며 실제 이름이 아니다.

1. 참조 획득: 30, 31, 29, 30, 31.
2. Segment 22–28의 P1을 차례로 호출.
3. 같은 segment의 P6 호출.
4. 참조 해제: 31, 30, 29, 31, 30. 이어서 복귀.

획득·해제는 `$9E/$15`, `$9E/$16`이다. Resident reference-count 경로와 normal PC+2,
nonresident loader 직전 경계를 확인했다. 실제 nonresident 읽기 전체를 검증한 것은 아니다.
`analysis/secondary-services.json`에 5개 서비스의 REA ID, sector 출처, 72개 검증 조건을 기록했다.
할당 위치 저장/복원 `$20/$21`, I/O result 읽기 `$22`도 포함한다.

## 게임 모드 필드와 분기

Root는 `table[29] + 2*45`의 word에서 **bits 8..11**을 읽는다.
정확한 식은 `(word >> 8) & 15`다. `04, 08, BA`는 width=4, shift=8이고
byte offset 4라는 뜻이 아니다. `table[29]`는 `$BD9E + 2*29`에 있는 pointer다.
Native assembler용 data base가 이 pointer +2인 경우와 혼동하지 않는다.

P6은 상태가 2 이하이면 P3, 그 외에는 P4를 호출하고, 상태가 11 이상이면 반복을 끝낸다.
P3는 상태가 3/4 또는 11 이상이 되면 반환한다. P4는 2 이하 또는 11 이상이면 반환한다.

| Dispatcher | 상태 | 해당 case의 호출 |
|---|---:|---|
| P3 | 0, 1 | segment 13 / P1 |
| P3 | 2 | segment 15 / P1 |
| P3 | 9 | segment 16 / P1; P3 자체 table에 존재하며 master 진입 조건과 구분 |
| P4 | 3, 4 | segment 21 / P1에 local 주소 8개 전달 |
| P4 | 5 | local[2]가 255이면 segment 17, 아니면 18 |
| P4 | 6 | signed local[2]가 3 이하면 segment 19, 아니면 20 |
| P4 | 7, 8, 10 | 같은 segment P5로 재분기 |
| P4 | 9 | segment 16 / P1 |
| P5 | 8 | segment 14 / P1 |
| P5 | 기타 | segment 8 / P1 |

P4는 각 반복에서 table[29]의 word index 347을 0으로 설정하고 index 33이 가리킨
값으로 할당 위치를 복원한다. Index 347의 이름을 아직 ‘취소’나 ‘종료’로 확정하지 않았다.
Segment 21에 전달하는 8개 참조 인자의 읽기/쓰기 계약과 local[2] event/action 값의 의미가 다음 분석 대상이다.

재현: `python3 tools/secondary_services.py`, `python3 tools/pcode_analysis.py`,
`python3 tools/startup_flow.py`. 결과는 `analysis/startup-control-flow.json`이며 case
cell 위치와 Play sector provenance를 포함한다. 시작 segment의 실제 disk 선택,
각 상태의 전체 역할·전이 주체, 각 장면 안의 규칙은 별도 미확인이다.
