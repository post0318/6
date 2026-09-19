// dataviz 스킬의 검증된 기본 팔레트(references/palette.md)에서 그대로 가져온 값.
// 색은 반드시 여기 정의된 슬롯만 사용하고, 임의의 색을 새로 만들지 않는다.

export const CHART_SURFACE = "#fcfcfb";
export const INK_PRIMARY = "#0b0b0b";
export const INK_SECONDARY = "#52514e";
export const INK_MUTED = "#898781";
export const GRIDLINE = "#e1e0d9";
export const BASELINE = "#c3c2b7";

// 카테고리 팔레트, palette.md 8슬롯 고정 순서 그대로:
// 1=blue 2=orange 3=aqua 4=yellow 5=magenta 6=green 7=violet 8=red
export const CATEGORICAL = {
  blue: "#2a78d6",
  orange: "#eb6834",
  aqua: "#1baf7a",
  yellow: "#eda100",
  magenta: "#e87ba4",
  green: "#008300",
  violet: "#4a3aa7",
  red: "#e34948",
};

// 후보 비교 차트처럼 임의 개수의 계열을 순서대로 색칠할 때 쓰는 고정 순서 배열
// (팔레트 슬롯 순서 = CVD 안전성의 핵심이므로 임의로 재배열하지 않는다)
export const CATEGORICAL_ORDER = [
  CATEGORICAL.blue,
  CATEGORICAL.orange,
  CATEGORICAL.aqua,
  CATEGORICAL.yellow,
  CATEGORICAL.magenta,
  CATEGORICAL.green,
  CATEGORICAL.violet,
  CATEGORICAL.red,
];

// 발산형(diverging) 쌍: blue <-> red, 중립 회색 중간값
export const DIVERGING = {
  positive: "#2a78d6",
  negative: "#e34948",
  neutral: "#f0efec",
};

// 순차형(sequential) ordinal 5단계 (light 표면 기준, step250부터 시작 — 표면보다 밝게 가지 않음)
export const SEQUENTIAL_ORDINAL_5 = [
  "#86b6ef", // step 250
  "#5598e7", // step 350
  "#256abf", // step 500
  "#184f95", // step 600
  "#0d366b", // step 700
];

// FG 극단 구간 참조선/음영 (텍스트 색은 아니고 배경 밴드용 — muted 톤)
export const EXTREME_FEAR_BAND = "rgba(227, 73, 72, 0.08)"; // red 계열, 저채도 배경
export const EXTREME_GREED_BAND = "rgba(11, 131, 0, 0.08)"; // green 계열, 저채도 배경
