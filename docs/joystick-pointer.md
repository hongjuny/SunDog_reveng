# 조이스틱 포인터의 원본 동작

원본은 조이스틱을 절대 좌표 입력으로 읽는다. `SYSTEM.LIBRARY` segment 22의
P42가 영역과 포인터 모양을 설정하고, P43이 P61 → native P5로 새 좌표를 읽는다.
이전 좌표와 달라졌을 때만 P41로 기존 포인터를 XOR하여 지우고, 좌표를 저장한 뒤
같은 P41로 새 포인터를 그린다. 이 경로에는 속도 누적이나 중앙 데드존 검사가 없다.
다른 설정 경로에 보정 기능이 존재하는지는 별도 문제다.

재현: `python3 tools/joystick_pointer_evidence.py`.
기계 판독 결과와 디스크 위치·해시는 [joystick-pointer.json](../analysis/joystick-pointer.json)에 있다.
원본 바이너리와 전체 디스어셈블은 공개 저장소에 포함하지 않는다.

|절차|segment 내 진입 오프셋|역할|
|---|---|---|
|P5|`$0DAA`|두 paddle timer 측정과 고정 보정|
|P30 / P31|`$0FA8` / `$0F6C`|16비트 좌측 / 부호 유지 우측 시프트|
|P37|`$06DA`|부호 있는 좌표 범위 제한|
|P41|`$06FA`|포인터 글리프 XOR 그리기|
|P42|`$079A`|영역·배율·중심 보정 설정과 최초 그리기|
|P43|`$0806`|변경된 좌표만 지우고 다시 그리기|
|P61|`$071A`|샘플링 → 배율 → 오프셋 → 범위 제한|
|P62|`$0774`|축별 배율과 중심 오프셋 계산|

주소는 디스크상의 segment 오프셋이다. 보존된 RAM 배치의 segment base는 `$95BE`이며,
따라서 native P5는 `$A368`이다. 고정 로드 주소로 일반화하지 않는다. P5의 최초 바이트는
Utility T13/S2, sector 내 `$AA`, `.do` offset `$D2AA`이다. P5는 다음 논리 sector까지 이어진다.
P41은 Utility T13/S9+$FA에서 시작한다. 나머지 시작 위치는 JSON에 기록한다.

## 두 축의 샘플링과 보정

P5는 `$C070`을 읽고 CPU X/Y를 0으로 만든다. `$C064`의 bit 7이 켜져 있는 동안
CPU **Y**를 증가시키고, `$C065`는 CPU **X**를 증가시킨다. 레지스터 이름과 화면 축을
혼동하면 안 된다. 출력 첫 word가 화면 X, 두 번째 word가 화면 Y이다.

`a=C064 counter`, `b=C065 counter`, `q=b//2`로 놓으면 정확한 변환은 다음과 같다.

```
rawX = clamp(a - 3, 0, 139)
rawY = clamp(q + ceil(q/2) - 5, 0, 95)
```

특히 `CLC; LSR zp; ADC zp`에서 **LSR이 carry를 다시 설정**한다.
따라서 `q+floor(q/2)`로 번역하면 홀수 q에서 한 칸 틀린다.
예: b=14일 때 q=7이며 rawY는 6이다.

Ghidra 12.1.4를 실제 provider로 사용한 REA 증거 ID는
`ev_e989c265fb5ba9e6ba1a7bc3ec18acdd914187aa5d4f3a6c89a1c25899c17f7d`이다.
증거 입력은 보존 RAM의 재배치된 P5이다. 원본의 `$0DD7` word `$001D`가 RAM에서는
JMP 목적지 `$A385`가 된다. 도구는 이 **단 하나의 차이**를 검증한 후 증거 SHA를 대조한다.
재배치된 파일과 원본 바이트가 같다고 주장하지 않는다.

모든 counter 조합 65,536개를 원본 post-MMIO 명령으로 실행하여 수식과 비교했다.
방문한 36개 instruction 시작 주소 모두 REA가 해석한 주소에 속한다.
추가로 선언된 유한 high-read 시퀀스 100개를 P5 전체에 공급하여 스택 복원·1회 strobe·
출력·256회 경계 counter wrap을 확인했다. 이것은 실제 기기의 전기 신호나 실행 속도 측정이 아니다.

NMOS 명령 cycle을 수작업으로 합산하면, `$C064` 읽기 명령에서 다음 반복의 같은 명령까지
계속 진행하는 세 분기는 각 22 cycle이다. 같은 반복의 `$C065` 읽기는 10 cycle 뒤다.
이 값은 명령의 정적 시간표이며 실제 조이스틱 계측값이 아니다. 8비트 counter에는 wrap이 있고,
관찰한 루프에는 timeout이 없다. 입력이 계속 high라면 종료가 보장되지 않는다.

## 화면 영역에 맞추는 방식

원본 rectangle word 순서는 bottom, top, right, left이다. P42는 다음 범위를 만든다.

|축|하한|상한|기준 span|double flag / offset table word|
|---|---|---|---|---|
|X|left+3|right−5|140|380 / 369|
|Y|top+5|bottom−3|96|379 / 368|

P62는 `span=upper-lower`에 대해 `scale=2 if span>nominal else 1`을 선택하고,
`offset=lower-((scale*nominal-span) >> 1)`을 계산한다. 우측 시프트는 native P31의
**부호 유지** 시프트다. P30/P31의 원본 코드를 576개 입력·시프트 조합으로 검증했다.
P61은 `clamp(scale*raw+offset,lower,upper)`를 출력한다.

전체 화면 rectangle `(0,279,0,191)`에서는 X가 `clamp(2*rawX-1,3,274)`,
Y가 `clamp(2*rawY+1,5,188)`이다. 초기 메뉴 rectangle `(135,270,90,181)`에서는
배율이 둘 다 1이고 오프셋은 X=132, Y=89이다. P42가 지정하는 범위가 입력 좌표의 의미를 바꾼다.

## 커서 보존과 남은 확인

P41은 P11(1)로 mode/mask를 지정하고 P12로 `(x−3,y+3)`에 위치를 설정한 뒤,
table 29 word 374의 글리프를 native P9로 그린다. 종료 시 P11(0)을 호출한다.
P11(1)은 mask 0, P11(0)은 mask 255를 설정한다. 기존 P9 분석의 XOR 합성과 결합하면
같은 위치에 같은 글리프를 다시 적용하여 배경을 복원한다는 설명이 성립한다.
이전 drawing mode를 보존했다가 복원하는 함수는 아니다.

P43의 비교 → erase → store → draw 순서는 원본 p-code의 정적 제어 흐름에서 확인했다.
동일 좌표이면 P41 호출이 생략된다. 버튼은 별도의 native P2/래치 경로이며 이 좌표 함수의
결과와 합쳐서 해석해야 한다. P3는 난수 함수이며 paddle reader가 아니다.

신뢰도: native 보정·시프트는 원본 바이트의 독립 실행과 실제 REA/Ghidra 해석이 일치하므로 높다.
p-code P41/P42/P43/P61/P62의 역할·축 매핑은 원본 디코드와 호출 순서에 근거한 정적 재구성으로 높다.
실제 원본 플레이 세션에서 이 전체 체인을 연속 실행한 검증은 아직 없다. 실제 조이스틱 보정,
극단적인 하드웨어 입력, scene별 포인터 모양 및 클릭 대상과의 연결은 추가 확인 대상이다.
