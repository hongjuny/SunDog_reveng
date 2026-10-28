# SHIP 마우스 조작

로컬 앱 `Build/SunDog.app` 0.7.0은 최초 SHIP에서 마우스로 포인터와 주인공을 조작한다.

- 마우스 이동: 원본 포인터 글리프를 이동한다.
- 왼쪽 버튼 유지: 주인공이 포인터를 향해 보행한다. 드래그로 목표를 바꿀 수 있다.
- 왼쪽 버튼 놓음: 이동을 멈추고 주인공이 도달한 위치의 시설을 판정한다.
- 오른쪽 버튼: 아직 포팅하지 않은 원본 모달 메뉴임을 알린다.
- 창/앱 비활성화: 이동을 취소하며 시설을 실행하지 않는다.

시설 선택은 현재 안내 메시지까지 연결된다. 조종석, 출입구, 다른 시설의 실제 장면 전환과 기능은 아직 구현하지 않았다. 주기적 세계 상태 갱신, 저장, 상태 표시도 포함하지 않는다. 이번 범위는 SHIP 내부 포인터·보행·충돌·대상 판정이다.

## 원본과 호스트 정책

`native/SunDogLogic/ShipInteraction.swift`는15P13/P14와22P22의 식을 Swift로 재작성한다. 제품에는6502/p-code 실행기가 없다. 원본 glyph12를 주인공 XOR 렌더링, glyph13을 충돌, glyph2를 포인터에 사용한다. glyph2는Play startup7P4 `$00EC–00ED`의 global298 초기화로 확인했다. 기존 검증 폰트 자원과 저장 word40/41에서 얻은 Bowie `(42,103)`을 사용한다. 원본 자원은 로컬 앱에만 복사되며 Git에는 포함하지 않는다.

충돌은 주인공과 포인터를 제외한 원본 배경에서 검사한다. 이는22P22가 주인공을 XOR로 지우고 P9 mode2로 검사하는 순서를 재구성한 것이다. SHIP global2=8의 원본 색 마스크 표에서 양쪽 바이트 마스크가7F임을 검사한다. 대각선→가로→세로, 실패 시1픽셀 재시도 순서를 유지한다. 포인터는15P11의 화면 사각형 축소 및22P42 inset을 반영하여 X3…267,Y5…180으로 제한한다.

macOS는 그림 위 NSView의 실제 크기로 마우스 좌표를280×192 논리 좌표에 대응시킨다. 여백은 입력 영역에 포함하지 않는다. `NSTrackingArea`, `mouseMoved`, `mouseDragged`, `mouseDown`, `mouseUp`을 연결한다. 키보드 Space/Return도 현재 포인터 위치에서 첫 버튼으로 사용할 수 있다.

호스트는33ms마다 이동 단계를 두 번 수행한다. 이는 사용 가능한 임시 페이싱이며 원본 Apple II 속도를 측정한 값이 아니다. 원본의 paddle timer 보정은 마우스 입력에는 적용하지 않는다. 원본 게임의 주기 처리24P9도 아직 실행하지 않는다.

## 재현과 검증

```sh
python3 tools/export_ship_interaction.py
python3 tools/verify_native_ship_interaction.py
python3 tools/build_native.py --tests --include-local-assets
python3 tools/verify_ship_mouse_app.py
open Build/SunDog.app
```

원본P9 mode2의 실제 바이트를 제한 분석 도구에서 실행한 결과와 Swift 충돌 판정1,440건을 비교했다. 원본 SHIP 배경·glyph13·색8 마스크를 사용하며 모든 결과가 일치한다. P14 원본CFG와 이미 대조된 분류식의45,220건도Swift와 일치한다. 원본 실행기는 오프라인 검증에만 쓰인다. native app 진단은 시작 위치42,103→마우스 목표80,100→이동77,103 및 버튼 해제 정지, 정지 상태 버튼 해제의action1 선택을 확인한다.

Swift 테스트에는 유지·놓음·중복 해제, 취소, 좌표 제한, 원본 배경 보존, 충돌 슬라이딩 및1픽셀 재시도를 포함한다. 검증 보고서는 `analysis/native-ship-interaction-verification.json`과 `analysis/ship-mouse-app-verification.json`이다. 실제 데스크톱의 OS 마우스 이벤트 전달과 창 표시를 자동 진단에서 관측했다고 주장하지 않는다.
