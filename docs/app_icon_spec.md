# 매일 동기부여 앱 아이콘 스펙

## 디자인 컨셉

- 다크 배경(#0f172a) 위에 큰따옴표(") 심볼을 primary 컬러(#38bdf8)로 배치
- 큰따옴표는 둥근 세리프 스타일, 굵은 웨이트
- 아이콘 하단에 얇은 수평 라인(#38bdf8, opacity 40%)으로 "밑줄" 느낌 부여
- 모서리: Android Adaptive Icon 규격 (원형 마스크 대응, safe zone 66% 내에 심볼 배치)

## 컬러

| 용도 | HEX |
|---|---|
| 배경 | #0f172a |
| 심볼 (큰따옴표) | #38bdf8 |
| 밑줄 액센트 | #38bdf8 (40% opacity) |

## 크기별 출력 (Android mipmap)

| 디렉토리 | 크기 (px) |
|---|---|
| mipmap-mdpi | 48 x 48 |
| mipmap-hdpi | 72 x 72 |
| mipmap-xhdpi | 96 x 96 |
| mipmap-xxhdpi | 144 x 144 |
| mipmap-xxxhdpi | 192 x 192 |

각 크기에 대해 `ic_launcher.png`와 `ic_launcher_round.png` 모두 생성.

## Adaptive Icon (Android 8.0+)

- foreground: 큰따옴표 심볼 (108x108 dp 기준, 중앙 72dp safe zone에 배치)
- background: 단색 #0f172a

## 생성 방법 (권장)

1. Figma 또는 Illustrator에서 1024x1024 마스터 아이콘 제작
2. Android Studio > Image Asset Studio로 import하여 자동 리사이징
3. 또는 https://icon.kitchen 에서 온라인 생성

## SVG 참고용 (1024x1024 기준)

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  <rect width="1024" height="1024" rx="224" fill="#0f172a"/>
  <text x="512" y="540" text-anchor="middle" dominant-baseline="central"
        font-family="Georgia, serif" font-size="560" font-weight="bold" fill="#38bdf8">
    &#x275D;
  </text>
  <line x1="280" y1="720" x2="744" y2="720" stroke="#38bdf8" stroke-opacity="0.4" stroke-width="12" stroke-linecap="round"/>
</svg>
```
