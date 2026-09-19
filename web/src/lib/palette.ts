// dataviz 스킬의 검증된 기본 팔레트(references/palette.md)에서 그대로 가져온 값.
// 색은 반드시 여기 정의된 슬롯만 사용하고, 임의의 색을 새로 만들지 않는다.

export const CHART_SURFACE = "#fcfcfb";
export const INK_PRIMARY = "#0b0b0b";
export const INK_SECONDARY = "#52514e";
export const INK_MUTED = "#898781";
export const GRIDLINE = "#e1e0d9";
export const BASELINE = "#c3c2b7";

// 카테고리 팔레트 (고정 순서, 슬롯 1=blue, 2=orange)
export const CATEGORICAL = {
  blue: "#2a78d6",
  orange: "#eb6834",
};

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
