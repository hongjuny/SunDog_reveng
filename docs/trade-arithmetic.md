# Segment 20 arithmetic helper — first native rule

원본 게임 segment 20의 P18은 external call이나 I/O가 없는 정수 산술 helper다.
이를 분석한 뒤 `native/SunDogLogic/GameIntegerScale.swift`로 같은 계산 순서를 구현했다.
거래 영역에 속한 함수지만, 이것만으로 가격·협상·재고 규칙 전체를 복원했다고 주장하지 않는다.

## 원본 계약

- Entry: segment offset `$0A70`. 정확한 Play track/sector와 이미지 offset은
  `analysis/trade-scaling-evidence.json`에 기록한다.
- Frame의 local[5]=x, local[4]=y, local[3]=divisor를 읽고 local[1]에 결과를 쓴다.
- Metadata의 parameter byte count는 10이다. Caller의 두 zero words가 local[1/2]에
  대응하고 local[2]는 이 body에서 쓰지 않는다. Short opcode `$DC/$DB/$DA`를
  각각 local[5/4/3]으로 확인했다. `$D8`이 local[0]이라는 가정은 틀리다.
- Return `$AD 01` 직전까지 원본 native interpreter handler 경로를 제한된 합성
  frame에 적용하고, 산술 식과 결과·stack 복원을 대조했다. 게임 실행기는 만들지 않았다.

현재 검증한 계약은 x=1..32767, y=0..32767, divisor=1..32767의 선택된 입력이다.
원본의 분기는 다음과 같다.

```text
if floor(32767 / x) <= y:
    result = signed16(x * floor(y / divisor))
else:
    result = trunc_zero(signed16(x * y) / divisor)
```

곱셈은 signed 16-bit bit pattern으로 wrap한다. 음수 입력의 계약은 아직 열지 않았고
Swift 함수는 해당 입력을 명시적으로 거부한다. x=0도 첫 나눗셈에서 오류 106에
도달한다. divisor=0 역시 오류 106이다. 임의로 0을 반환하도록 바꾸지 않는다.

## 보존해야 하는 반올림 경계

| x | y | divisor | 원본 결과 | 경로 |
|---:|---:|---:|---:|---|
| 8 | 4094 | 8 | 4094 | 곱한 뒤 나눔 |
| 8 | 4095 | 8 | 4088 | 먼저 나눈 뒤 곱함 |
| 8 | 4096 | 8 | 4096 | 먼저 나눈 뒤 곱함 |
| 8 | 5000 | 3 | 13328 | 먼저 나눈 뒤 곱함 |

마지막 행을 보통의 `x*y/divisor`로 단순화하면 13333이 되어 원본과 달라진다.
이 불연속을 정리하거나 ‘개선’하지 않았다. 733개 입력과 zero-error 3개를 확인했고,
동일한 733개 결과가 실제 컴파일한 Swift 함수와 일치한다. 전 입력의 수학적 증명이나
전체 거래 기능의 호환성 검증은 아니다.

P17은 이 helper를 두 번 호출한다. 앞선 차이 값의 절댓값에 8을 더한 factor를 만들고,
한 분기에서는 factor×value/8, 다른 분기에서는 8×value/factor 형식을 사용한다.
이 값이 어떤 가격/물품 필드인지와 실제 범위, P23 caller의 잔액·재고 부작용은
추가 data-flow 분석이 필요하다.

재현:

```sh
python3 tools/trade_scaling_evidence.py
python3 tools/verify_native_rules.py
```

두 검증 결과는 `analysis/trade-scaling-evidence.json`,
`analysis/native-rule-verification.json`이다. 합성 사례의 상세 값은 local에 보관한다.
