# Apple II fidelity specification — provisional

목표는 Apple II v2.0의 그림, 글꼴, UI 배치와 게임 동작을 유지하는 macOS 앱이다.
첫 기준 환경은 Apple II Plus / NMOS 6502 / Language Card다. 현재 달성한 범위는
원본 실행 캡처에서 얻은 HGR RAM을 Swift로 다시 그리는 것이다.

## 영상 기준

- HGR visible memory: 192 rows × 40 bytes; 8 KiB page의 padding은 화면에 넣지 않는다.
- 논리적 가로 280 bits를 560×192 RGBA samples로 해석한다. byte 경계의 이웃 bit와
  high-bit phase를 포함한다. 텍스트는 원본 HGR 메모리의 도형으로 보존한다.
- 디지털 색상 preset은 `a2m-hgr-colour-v1`이다. a2m의 3-bit neighbor window와
  palette에 맞추며 아날로그 NTSC 신호나 실물 모니터 색상의 최종 기준으로 삼지 않는다.
- 현재 지원 모드는 TEXT=0, HIRES=1, MIXED=0, COL80=0, 80STORE=0의 full-screen HGR다.
  PAGE2가 명시된 page 1/2를 읽는다. text/mixed/auxiliary mode는 오류로 분리한다.
- 앱은 nearest sampling으로 표시하며 4:3, 280:192, raw 560:192 비율을 제공한다.
  기본 4:3은 잠정 표시 정책이다. 결정적 비교는 비율 변경 전 raw samples에서 한다.

`analysis/video-comparison.json`의 기준 실행 캡처 24개가 Swift CPU decoder와
0 differing pixels다. 잘못된 초기 channel 변환 7개는 제외하고 text mode 2개는
미지원으로 기록했다. 이는 같은 digital preset의 일치를 검증한 결과다.
Metal 코드는 컴파일했지만 현재 agent 실행 환경에서 device가 없어 GPU 동등성을
검증하지 못했다. 디스플레이의 색 관리 결과와 실제 창의 외관도 별도 확인이 필요하다.

## 다음 통과 조건

1. Utility와 Play의 입력·장면 전환 기준 trace 확보; 알려지지 않은 sector 읽기는 별도 처리.
2. 포팅 실행 코어가 같은 p-code 경계의 메모리, bank, disk 요청을 재현.
3. UI·커서·페이지 전환·필요한 영상 모드별 캡처 비교와 GPU readback 비교 통과.
4. 가상 clock 기준 입력 replay 및 저장·재실행 왕복 검증.
5. 대상 Mac의 실제 창, 키 focus, 화면 비율과 색상 표시를 확인.

범용 에뮬레이터의 현재 출력만으로 실물 Apple II의 색·속도 충실도를 확정하지 않는다.
