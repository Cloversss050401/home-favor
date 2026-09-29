<template>
  <!-- 原创手绘涂鸦风插画：彩色版（界面用） + 涂鸦线条版（背景装饰，带淡色点缀+装饰元素） -->
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 48 48"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <!-- ============ 涂鸦线条模式（背景装饰：随性线条 + 淡色填充 + 点缀） ============ -->
    <template v-if="line">
      <!-- 厨师帽（带笑脸+爱心点缀） -->
      <g v-if="name === 'chef'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 30v-7a12 12 0 0 1 24 0v7" stroke-width="2.7" />
        <path d="M9 30h30" stroke-width="2.7" />
        <path d="M17 24h14M20 18h8M15 21h5" stroke-width="1.2" opacity="0.5" />
        <path d="M14 30h20v6a10 8 0 0 1-20 0Z" stroke-width="1.5" />
        <circle cx="19" cy="33" r="1.1" fill="#2F6B4F" stroke="none" />
        <circle cx="29" cy="33" r="1.1" fill="#2F6B4F" stroke="none" />
        <path d="M20 37q4 3 8 0" stroke-width="1.4" />
        <path d="M34 16c.8-2 3-2 3.6-.8.6 2-1.4 3.4-3.6 4.6-2.2-1.2-4.2-2.6-3.6-4.6.6-1.2 2.8-1.2 3.6.8" stroke-width="1.2" fill="#5d8d74" fill-opacity="0.35" />
      </g>

      <!-- 汤锅（带笑脸+热气+淡色锅身） -->
      <g v-else-if="name === 'pot'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M8 24a16 8 0 0 0 32 0Z" fill="#5d8d74" fill-opacity="0.16" stroke-width="2.7" />
        <path d="M10 24h28" stroke-width="2.7" />
        <path d="M38 26h8" stroke-width="2.7" />
        <path d="M21 13l-2-4M27 12l-2-4M33 13l-2-4" stroke-width="1.3" opacity="0.6" />
        <circle cx="20" cy="21" r="1.1" fill="#2F6B4F" stroke="none" />
        <circle cx="28" cy="21" r="1.1" fill="#2F6B4F" stroke="none" />
        <path d="M21 25q3 2.4 6 0" stroke-width="1.4" />
        <path d="M42 18h2.6M43.3 16.7v2.6" stroke-width="1.4" opacity="0.7" />
      </g>

      <!-- 热汤碗（带笑脸+爱心+淡色汤面） -->
      <g v-else-if="name === 'soup'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M10 25a9 9 0 0 0 28 0 14 8 0 0 0-28 0Z" stroke-width="2.7" />
        <path d="M11 24.5a13 7 0 0 0 26 0" fill="#5d8d74" fill-opacity="0.2" stroke-width="1.5" />
        <path d="M19 13c-1.4-2 .6-3.6-.6-5.4M26 12c-1.4-2 .6-3.6-.6-5.4M32 13.5c-1.4-2 .6-3.6-.6-5.4" stroke-width="1.3" opacity="0.6" />
        <circle cx="19" cy="22" r="1.1" fill="#2F6B4F" stroke="none" />
        <circle cx="27" cy="22" r="1.1" fill="#2F6B4F" stroke="none" />
        <path d="M20 25q3 2.4 6 0" stroke-width="1.4" />
        <path d="M36 13c1-3 4-3 5-1 1 3-2 5-5 7-3-2-6-4-5-7 1-2 4-2 5 1" stroke-width="1.3" fill="#5d8d74" fill-opacity="0.35" />
      </g>

      <!-- 小鱼（带笑脸+水花） -->
      <g v-else-if="name === 'fish'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 24c6-8 22-8 28 0-6 8-22 8-28 0Z" fill="#5d8d74" fill-opacity="0.14" stroke-width="2.7" />
        <path d="M37 24l8-7M37 24l8 7" stroke-width="2.4" />
        <path d="M29 16l-3 3M29 32l-3-3M12 20l-2 2" stroke-width="1.3" opacity="0.55" />
        <circle cx="16" cy="22" r="1.1" fill="#2F6B4F" stroke="none" />
        <path d="M15 27q4 2 8 0" stroke-width="1.4" />
        <path d="M9 13l1.8-2.4M11 13l-1.8-2.4" stroke-width="1.1" opacity="0.6" />
      </g>

      <!-- 面包（带笑脸+芝麻粒） -->
      <g v-else-if="name === 'bread'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 21c0-6 4-9 10-9s10 3 10 9v11a3 3 0 0 1-3 3H17a3 3 0 0 1-3-3Z" fill="#5d8d74" fill-opacity="0.12" stroke-width="2.7" />
        <path d="M17 21h14" stroke-width="1.4" opacity="0.6" />
        <circle cx="20" cy="25" r="1.1" fill="#2F6B4F" stroke="none" />
        <circle cx="28" cy="25" r="1.1" fill="#2F6B4F" stroke="none" />
        <path d="M21 29q3 2.4 6 0" stroke-width="1.4" />
        <path d="M23 15h1M27 16h1M25 12.5h1" stroke-width="1.2" opacity="0.7" />
      </g>

      <!-- 苹果（手绘轮廓+笑脸+淡色果身+叶） -->
      <g v-else-if="name === 'apple'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M24 16c-7 0-11 5-11 11 0 7 5 11 11 11s11-4 11-11c0-6-4-11-11-11Z" fill="#5d8d74" fill-opacity="0.14" stroke-width="2.7" />
        <path d="M24 16v-4" stroke-width="1.8" />
        <path d="M26 15c2-4 6-4 8-1 1 3-3 6-8 3Z" fill="#5d8d74" fill-opacity="0.35" stroke-width="1.4" opacity="0.8" />
        <circle cx="20" cy="23" r="1.1" fill="#2F6B4F" stroke="none" />
        <circle cx="28" cy="23" r="1.1" fill="#2F6B4F" stroke="none" />
        <path d="M21 27q3 2.4 6 0" stroke-width="1.4" />
      </g>

      <!-- 茶壶（带笑脸+蒸汽+淡色壶身） -->
      <g v-else-if="name === 'teapot'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 26a10 10 0 0 0 20 0Z" fill="#5d8d74" fill-opacity="0.14" stroke-width="2.7" />
        <path d="M14 26h20" stroke-width="2.7" />
        <path d="M6 26h8" stroke-width="2.7" />
        <path d="M34 28c3 0 5 3 5 7s-2 7-5 7" stroke-width="2.4" />
        <path d="M24 18v-6M24 12c0-2 2-3 3-2" stroke-width="1.8" opacity="0.7" />
        <circle cx="19" cy="23" r="1.1" fill="#2F6B4F" stroke="none" />
        <circle cx="29" cy="23" r="1.1" fill="#2F6B4F" stroke="none" />
        <path d="M20 27q4 2.4 8 0" stroke-width="1.4" />
        <path d="M6 20h-2.4M6 18.8v2.4" stroke-width="1.3" opacity="0.7" />
      </g>

      <!-- 锅铲（淡色铲头+柄装饰） -->
      <g v-else-if="name === 'spatula'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M25 6v22" stroke-width="2.6" />
        <path d="M14 30h22l-3 9a4 4 0 0 1-4 3h-8a4 4 0 0 1-4-3Z" fill="#5d8d74" fill-opacity="0.16" stroke-width="2.6" />
        <path d="M25 24v6M18 31h14M19 36h10" stroke-width="1.3" opacity="0.55" />
        <path d="M26.5 9c-1.2 1.6 0 2.8-1 4" stroke-width="1.2" opacity="0.6" />
      </g>

      <!-- 汤勺（淡色勺头） -->
      <g v-else-if="name === 'ladle'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M25 6v20" stroke-width="2.6" />
        <circle cx="25" cy="32" r="7" fill="#5d8d74" fill-opacity="0.16" stroke-width="2.6" />
        <path d="M25 12v6M22 34h6" stroke-width="1.3" opacity="0.55" />
      </g>

      <!-- 菜刀（淡色刀身+装饰线） -->
      <g v-else-if="name === 'knife'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M13 10c11 0 13 14 7 22l-9-2c1-7 0-16 2-20Z" fill="#5d8d74" fill-opacity="0.14" stroke-width="2.6" />
        <path d="M17 32h9l-2 8h-7l-4-5" stroke-width="2.4" />
        <path d="M15 15c3 1 5 6 5 10" stroke-width="1.2" opacity="0.5" />
      </g>

      <!-- 胡萝卜（带笑脸+淡色+叶） -->
      <g v-else-if="name === 'carrot'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M15 39 31 15a5 5 0 0 1 7 7L23 39a9 9 0 0 1-8 2Z" fill="#5d8d74" fill-opacity="0.18" stroke-width="2.6" />
        <path d="M30 16 35 11M27 15l-3-5" stroke-width="1.6" opacity="0.7" />
        <circle cx="22" cy="27" r="1.1" fill="#2F6B4F" stroke="none" />
        <circle cx="27" cy="22" r="1.1" fill="#2F6B4F" stroke="none" />
        <path d="M20 30q3 2 6 0" stroke-width="1.4" />
        <path d="M38 24c-1 2 1 3.4 0 5" stroke-width="1.2" opacity="0.6" />
      </g>

      <!-- 西兰花（带笑脸+淡色花球） -->
      <g v-else-if="name === 'broccoli'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 42V30" stroke-width="3" />
        <circle cx="24" cy="26" r="7.4" fill="#5d8d74" fill-opacity="0.16" stroke-width="2.4" />
        <circle cx="16" cy="28" r="5.4" stroke-width="1.8" opacity="0.6" />
        <circle cx="32" cy="28" r="5.4" stroke-width="1.8" opacity="0.6" />
        <circle cx="20" cy="21" r="5" stroke-width="1.8" opacity="0.75" />
        <circle cx="28" cy="21" r="5" stroke-width="1.8" opacity="0.75" />
        <circle cx="24" cy="17.5" r="4.6" stroke-width="1.8" opacity="0.9" />
        <circle cx="22" cy="26" r="1" fill="#2F6B4F" stroke="none" />
        <circle cx="26" cy="26" r="1" fill="#2F6B4F" stroke="none" />
        <path d="M21 28q3 1.8 6 0" stroke-width="1.3" />
      </g>

      <!-- 牛奶盒（带笑脸+淡色盒身） -->
      <g v-else-if="name === 'milk'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M17 13h14l4 4v20a3 3 0 0 1-3 3H16a3 3 0 0 1-3-3V17Z" fill="#5d8d74" fill-opacity="0.12" stroke-width="2.6" />
        <path d="M17 13h14" stroke-width="1.6" />
        <path d="M19 22h10v8a3 3 0 0 1-3 3h-4a3 3 0 0 1-3-3Z" stroke-width="1.5" opacity="0.6" />
        <circle cx="21" cy="27" r="1" fill="#2F6B4F" stroke="none" />
        <circle cx="27" cy="27" r="1" fill="#2F6B4F" stroke="none" />
        <path d="M22 30q2 1.6 4 0" stroke-width="1.3" />
      </g>

      <!-- 鸡蛋（带笑脸+淡色蛋身） -->
      <g v-else-if="name === 'egg'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M24 7c-8 6-10 18-6 24a8 8 0 0 0 12 0c4-6 2-18-6-24Z" fill="#5d8d74" fill-opacity="0.14" stroke-width="2.6" />
        <circle cx="20" cy="22" r="1.1" fill="#2F6B4F" stroke="none" />
        <circle cx="28" cy="22" r="1.1" fill="#2F6B4F" stroke="none" />
        <path d="M21 26q3 2.4 6 0" stroke-width="1.4" />
        <path d="M13 30h-3" stroke-width="1.2" opacity="0.6" />
      </g>

      <!-- 草莓（带笑脸+淡色果身） -->
      <g v-else-if="name === 'strawberry'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M24 10c-6 0-11 6-11 12a11 11 0 0 0 22 0c0-6-5-12-11-12Z" fill="#5d8d74" fill-opacity="0.15" stroke-width="2.6" />
        <path d="M24 10V6" stroke-width="1.8" />
        <path d="M18 17c1 3-1 5 1 8M25 14c1 3-1 5 1 8" stroke-width="1.2" opacity="0.55" />
        <circle cx="22" cy="20" r="1" fill="#2F6B4F" stroke="none" />
        <circle cx="27" cy="21" r="1" fill="#2F6B4F" stroke="none" />
        <path d="M21 25q3 2 6 0" stroke-width="1.3" />
      </g>

      <!-- 平底锅（煎蛋带笑脸+彩色蛋黄） -->
      <g v-else-if="name === 'pan'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M7 20a14 9 0 0 0 28 0 14 9 0 0 0-28 0Z" fill="#5d8d74" fill-opacity="0.12" stroke-width="2.7" />
        <path d="M35 18h9a2.6 2.6 0 0 1 0 5.2h-7.2" stroke-width="2.7" />
        <path d="M11 21a10 6.2 0 0 0 20 0 10 6.2 0 0 0-20 0Z" stroke-width="1.5" opacity="0.7" />
        <circle cx="23" cy="20.5" r="4.6" fill="#5d8d74" fill-opacity="0.75" stroke-width="1.5" />
        <circle cx="21" cy="19.5" r="0.9" fill="#2F6B4F" stroke="none" />
        <circle cx="25" cy="19.5" r="0.9" fill="#2F6B4F" stroke="none" />
        <path d="M21.5 22.5q1.5 1.2 3 0" stroke-width="1.2" />
      </g>

      <!-- 橙子（带笑脸+淡色果身） -->
      <g v-else-if="name === 'orange'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="25" cy="25" r="13" fill="#5d8d74" fill-opacity="0.16" stroke-width="2.6" />
        <path d="M15 21a13 13 0 0 0 20 8M17 27a13 13 0 0 1 16-4" stroke-width="1.3" opacity="0.5" />
        <path d="M28 13c4-2 5-5 4-7-3-1-6 1-7 5" fill="#5d8d74" fill-opacity="0.35" stroke-width="1.6" opacity="0.8" />
        <circle cx="21" cy="22" r="1.1" fill="#2F6B4F" stroke="none" />
        <circle cx="29" cy="22" r="1.1" fill="#2F6B4F" stroke="none" />
        <path d="M22 26q3 2.4 6 0" stroke-width="1.4" />
      </g>

      <!-- 爱心（淡色填充） -->
      <g v-else-if="name === 'heart'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M24 39c-8-5-12-9-12-14a6 6 0 0 1 12-2 6 6 0 0 1 12 2c0 5-4 9-12 14Z" fill="#5d8d74" fill-opacity="0.2" stroke-width="2.4" />
        <path d="M20 22c-1 2-1 4 0 6" stroke-width="1.2" opacity="0.5" />
      </g>

      <!-- 枝叶（淡色叶子） -->
      <g v-else-if="name === 'leaf'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 36c10-14 18-18 26-20" stroke-width="2.2" />
        <path d="M20 27c4-4 8-5 12-4M26 21c3-3 7-4 11-4" stroke-width="1.4" opacity="0.6" />
        <path d="M32 20c-1 3-2 6-4 9" stroke-width="1.3" opacity="0.55" />
        <path d="M20 27c2 4 4 6 6 7M26 21c2 3 3 5 3 8" stroke-width="1.2" opacity="0.5" />
      </g>

      <!-- 加号（装饰） -->
      <g v-else-if="name === 'plus'" stroke="#2F6B4F" stroke-linecap="round" stroke-width="1.6">
        <path d="M24 15v18M15 24h18" />
      </g>

      <!-- 星点（装饰） -->
      <g v-else-if="name === 'star'" fill="#5d8d74" stroke="#2F6B4F" stroke-width="1.4" stroke-linejoin="round">
        <path d="M24 14l2.4 5 5.4.6-4 3.6 1 5.4-4.8-2.8-4.8 2.8 1-5.4-4-3.6 5.4-.6Z" fill-opacity="0.7" />
      </g>

      <!-- 纸杯蛋糕 -->
      <g v-else-if="name === 'cupcake'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M15 26h18l-2.4 12a3 3 0 0 1-3 2.6h-7.2a3 3 0 0 1-3-2.6Z" fill="#5d8d74" fill-opacity="0.14" stroke-width="2.6" />
        <path d="M13 26a11 7.5 0 0 1 22 0" stroke-width="2.6" />
        <path d="M19 31v4M24 32v4M29 31v4" stroke-width="1.2" opacity="0.55" />
        <circle cx="24" cy="14.5" r="2.6" fill="#5d8d74" fill-opacity="0.35" stroke-width="1.6" />
        <circle cx="20" cy="21" r="1" fill="#2F6B4F" stroke="none" />
        <circle cx="28" cy="21" r="1" fill="#2F6B4F" stroke="none" />
        <path d="M21 23.5q3 2.2 6 0" stroke-width="1.3" />
      </g>

      <!-- 牛角包 -->
      <g v-else-if="name === 'croissant'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M11 30c-2-8 4-15 13-15s15 7 13 15c-1.4 4.4-6.6 4-9 1.2-1 1.5-2.4 2.3-4 2.3s-3-.8-4-2.3c-2.4 2.8-7.6 3.2-9-1.2Z" fill="#5d8d74" fill-opacity="0.14" stroke-width="2.6" />
        <path d="M19 22c1.6-1.8 3.4-2.6 5-2.6s3.4.8 5 2.6" stroke-width="1.3" opacity="0.6" />
        <circle cx="20" cy="27" r="1" fill="#2F6B4F" stroke="none" />
        <circle cx="28" cy="27" r="1" fill="#2F6B4F" stroke="none" />
        <path d="M21 29.5q3 2.2 6 0" stroke-width="1.3" />
      </g>

      <!-- 法棍 -->
      <g v-else-if="name === 'baguette'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 36 32 12a5.6 5.6 0 0 1 8 8L20 40a5.6 5.6 0 0 1-8-4Z" fill="#5d8d74" fill-opacity="0.16" stroke-width="2.6" />
        <path d="M19 31c1-2 2.6-3 4.6-3M24 26c1-2 2.6-3 4.6-3M29 21c1-2 2.6-3 4.6-3" stroke-width="1.3" opacity="0.6" />
        <circle cx="16" cy="34" r="0.9" fill="#2F6B4F" stroke="none" />
        <circle cx="19.5" cy="36" r="0.9" fill="#2F6B4F" stroke="none" />
        <path d="M15.5 37.5q2 1.4 4.2.2" stroke-width="1.2" />
      </g>

      <!-- 碱水结 -->
      <g v-else-if="name === 'pretzel'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M13 35c-3.4-2-5.4-5.6-5.4-9.6 0-6 4.6-9.6 9-8.2 2.8.9 4.8 3.4 7.4 7.8 2.6-4.4 4.6-6.9 7.4-7.8 4.4-1.4 9 2.2 9 8.2 0 4-2 7.6-5.4 9.6l-11 6.6Z" fill="#5d8d74" fill-opacity="0.12" stroke-width="2.6" />
        <path d="M17 33l14-9" stroke-width="1.3" opacity="0.6" />
        <circle cx="16" cy="20.5" r="0.9" fill="#2F6B4F" stroke="none" />
        <circle cx="24" cy="17.5" r="0.9" fill="#2F6B4F" stroke="none" />
        <circle cx="32" cy="20.5" r="0.9" fill="#2F6B4F" stroke="none" />
        <circle cx="20" cy="26.5" r="1" fill="#2F6B4F" stroke="none" />
        <circle cx="28" cy="26.5" r="1" fill="#2F6B4F" stroke="none" />
        <path d="M21 29.5q3 2.2 6 0" stroke-width="1.3" />
      </g>

      <!-- 奶酪 -->
      <g v-else-if="name === 'cheese'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M10 31 36 17v15a4 4 0 0 1-4 4H14a4 4 0 0 1-4-4Z" fill="#5d8d74" fill-opacity="0.16" stroke-width="2.6" />
        <circle cx="19" cy="30" r="2.1" stroke-width="1.3" opacity="0.65" />
        <circle cx="27" cy="26" r="1.5" stroke-width="1.3" opacity="0.65" />
        <circle cx="25" cy="33" r="1.1" stroke-width="1.2" opacity="0.65" />
        <circle cx="31" cy="31.5" r="1" fill="#2F6B4F" stroke="none" />
        <circle cx="34.5" cy="31.5" r="0.9" fill="#2F6B4F" stroke="none" />
        <path d="M31 34q1.8 1.4 3.6 0" stroke-width="1.2" />
      </g>

      <!-- 甜甜圈 -->
      <g v-else-if="name === 'donut'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="24" cy="26" r="12" fill="#5d8d74" fill-opacity="0.14" stroke-width="2.6" />
        <circle cx="24" cy="26" r="4.6" stroke-width="2" />
        <path d="M14 22c1.8-2.2 3.2.8 5-1.4s3.2.8 5-1.4 3.2.8 5-1.4 3.2-.8 5 1.4" stroke-width="1.3" opacity="0.6" />
        <path d="M17.5 17.5l1.6 1.2M30 17l-1.4 1.4M18 33.6l1.6-1M29.6 33.4l-1.4-1.2" stroke-width="1.2" opacity="0.55" />
        <circle cx="18.6" cy="25" r="1" fill="#2F6B4F" stroke="none" />
        <circle cx="29.4" cy="25" r="1" fill="#2F6B4F" stroke="none" />
      </g>

      <!-- 外带咖啡 -->
      <g v-else-if="name === 'coffee'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M15.5 19h17l-2.1 19a3 3 0 0 1-3 2.8h-6.8a3 3 0 0 1-3-2.8Z" fill="#5d8d74" fill-opacity="0.14" stroke-width="2.6" />
        <path d="M13.5 19h21M17 14.5h14" stroke-width="2.2" />
        <path d="M27.5 14.5 31 8" stroke-width="2" />
        <path d="M18.5 26.5h11" stroke-width="1.3" opacity="0.6" />
        <circle cx="21" cy="31" r="1" fill="#2F6B4F" stroke="none" />
        <circle cx="27" cy="31" r="1" fill="#2F6B4F" stroke="none" />
        <path d="M22 33.6q2 1.8 4 0" stroke-width="1.2" />
      </g>

      <!-- 打蛋器 -->
      <g v-else-if="name === 'whisk'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21.5 7h5v10h-5Z" fill="#5d8d74" fill-opacity="0.16" stroke-width="2.4" />
        <path d="M21.5 17c-6 4.2-8.2 10-6.2 14.4C16.8 34.4 20 36 24 36s7.2-1.6 8.7-4.6c2-4.4-.2-10.2-6.2-14.4" stroke-width="2.6" />
        <path d="M24 17c-3.2 4.2-4.4 9-3.4 13 .7 2.8 2 3.4 3.4 3.4s2.7-.6 3.4-3.4c1-4-.2-8.8-3.4-13Z" stroke-width="1.3" opacity="0.6" />
        <path d="M37 12v5M34.5 14.5h5" stroke-width="1.4" opacity="0.7" />
      </g>

      <!-- 三明治 -->
      <g v-else-if="name === 'sandwich'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 29h24v5.6a3.4 3.4 0 0 1-3.4 3.4H15.4a3.4 3.4 0 0 1-3.4-3.4Z" fill="#5d8d74" fill-opacity="0.12" stroke-width="2.6" />
        <path d="M12 29c1.6-2.8 3.4.8 5.4-2s3.8.8 5.8-2 3.8.8 5.8 2 3.4-.8 5 2" stroke-width="1.4" opacity="0.65" />
        <path d="M12 29c0-6.4 5.4-11 12-11s12 4.6 12 11" fill="#5d8d74" fill-opacity="0.14" stroke-width="2.6" />
        <circle cx="21" cy="24" r="1" fill="#2F6B4F" stroke="none" />
        <circle cx="27" cy="24" r="1" fill="#2F6B4F" stroke="none" />
        <path d="M22 26.4q2 1.8 4 0" stroke-width="1.2" />
      </g>

      <!-- 鸡尾酒 -->
      <g v-else-if="name === 'cocktail'" stroke="#2F6B4F" stroke-linecap="round" stroke-linejoin="round">
        <path d="M13 12h22l-9.2 11.4a1.8 1.8 0 0 1-3.6 0Z" fill="#5d8d74" fill-opacity="0.14" stroke-width="2.6" />
        <path d="M24 25v8M18 37h12" stroke-width="2.2" />
        <path d="M17 16.4h14" stroke-width="1.3" opacity="0.6" />
        <circle cx="31" cy="9" r="2.6" fill="#5d8d74" fill-opacity="0.35" stroke-width="1.6" />
        <path d="M31 6.6c.8-1.8 2-2.8 3.8-3" stroke-width="1.2" />
        <circle cx="21" cy="18.6" r="1" fill="#2F6B4F" stroke="none" />
        <circle cx="27" cy="18.6" r="1" fill="#2F6B4F" stroke="none" />
        <path d="M22 21q2 1.8 4 0" stroke-width="1.2" />
      </g>

      <!-- line 模式兜底 -->
      <g v-else stroke="#2F6B4F" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M10 25a9 9 0 0 0 28 0 14 8 0 0 0-28 0Z" />
        <path d="M11 24.5a13 7 0 0 0 26 0" stroke-width="1.4" />
      </g>
    </template>

    <!-- ============ 彩色卡通版（界面内使用） ============ -->
    <template v-else>
      <!-- 煎蛋锅（品牌/菜单用） -->
      <g v-if="name === 'pan'">
        <path d="M7 20a14 9 0 0 0 28 0 14 9 0 0 0-28 0Z" fill="#2F6B4F" />
        <path d="M35 18h9a2.6 2.6 0 0 1 0 5.2h-7.2" stroke="#24563F" stroke-width="3" stroke-linecap="round" />
        <path d="M11 21a10 6.2 0 0 0 20 0 10 6.2 0 0 0-20 0Z" fill="#E9F1EC" />
        <circle cx="21" cy="21.5" r="3.4" fill="#8AADA0" />
        <circle cx="23.6" cy="19.6" r="0.9" fill="#A87B2A" />
      </g>

      <!-- 热汤碗（空态/装饰） -->
      <g v-else-if="name === 'soup'">
        <path d="M10 25a9 9 0 0 0 28 0 14 8 0 0 0-28 0Z" fill="#2F6B4F" />
        <path d="M11 24.5a13 7 0 0 0 26 0" fill="#E9F1EC" />
        <circle cx="17" cy="24" r="1.6" fill="#A87B2A" />
        <path d="M23 25.5a2.6 2.6 0 0 0 2.4 1.6 2.6 2.6 0 0 0 2.4-1.6" stroke="#8AADA0" stroke-width="1.8" fill="none" stroke-linecap="round" />
        <path d="M19 13.5c-1.4-2 .6-3.4-.6-5" stroke="#8AADA0" stroke-width="2.4" stroke-linecap="round" fill="none" />
        <path d="M26 12.5c-1.4-2 .6-3.4-.6-5" stroke="#8AADA0" stroke-width="2.4" stroke-linecap="round" fill="none" />
        <path d="M32 14c-1.4-2 .6-3.4-.6-5" stroke="#8AADA0" stroke-width="2.4" stroke-linecap="round" fill="none" />
      </g>

      <!-- 胡萝卜 -->
      <g v-else-if="name === 'carrot'">
        <path d="M15 39 31 15a5 5 0 0 1 7 7L23 39a9 9 0 0 1-8 2Z" fill="#2F6B4F" />
        <path d="M30 16 34 11" stroke="#8AADA0" stroke-width="2.4" stroke-linecap="round" />
        <path d="M27 15l-3-5" stroke="#8AADA0" stroke-width="2.4" stroke-linecap="round" />
        <path d="M22 21l-2.4-2.4M26 26l-2.4-2.4" stroke="#A87B2A" stroke-width="1.6" stroke-linecap="round" />
      </g>

      <!-- 橙子 -->
      <g v-else-if="name === 'orange'">
        <circle cx="25" cy="25" r="13" fill="#8AADA0" />
        <path d="M15 21a13 13 0 0 0 20 8" stroke="#A87B2A" stroke-width="1.6" stroke-linecap="round" fill="none" />
        <path d="M17 27a13 13 0 0 1 16-4" stroke="#A87B2A" stroke-width="1.6" stroke-linecap="round" fill="none" />
        <path d="M28 13c4-2 5-5 4-7-3-1-6 1-7 5" fill="#8AADA0" />
      </g>

      <!-- 牛奶盒 -->
      <g v-else-if="name === 'milk'">
        <path d="M17 13h14l4 4v20a3 3 0 0 1-3 3H16a3 3 0 0 1-3-3V17Z" fill="#FFFFFF" />
        <path d="M17 13h14" stroke="#24563F" stroke-width="2" />
        <rect x="19" y="20" width="10" height="12" rx="2" fill="#E9F1EC" />
        <path d="M21 26h6M21 29h4" stroke="#2F6B4F" stroke-width="1.6" stroke-linecap="round" />
      </g>

      <!-- 西兰花 -->
      <g v-else-if="name === 'broccoli'">
        <path d="M21 42V30" stroke="#5d8d74" stroke-width="3.4" stroke-linecap="round" />
        <circle cx="24" cy="26" r="7.4" fill="#8AADA0" />
        <circle cx="16" cy="28" r="5.4" fill="#8AADA0" />
        <circle cx="32" cy="28" r="5.4" fill="#8AADA0" />
        <circle cx="20" cy="21" r="5" fill="#5d8d74" />
        <circle cx="28" cy="21" r="5" fill="#5d8d74" />
        <circle cx="24" cy="17.5" r="4.6" fill="#8AADA0" />
      </g>

      <!-- 米饭碗（带热气） -->
      <g v-else-if="name === 'rice'">
        <path d="M8 30a9 9 0 0 0 32 0 16 7 0 0 0-32 0Z" fill="#2F6B4F" />
        <path d="M10 29.5a14 6 0 0 0 28 0" fill="#FFFFFF" />
        <circle cx="17" cy="26" r="2" fill="#E9F1EC" />
        <circle cx="24" cy="25" r="2.4" fill="#E9F1EC" />
        <circle cx="31" cy="26" r="2" fill="#E9F1EC" />
        <path d="M19 17c-1.4-2 .6-3.4-.6-5" stroke="#8AADA0" stroke-width="2.4" stroke-linecap="round" fill="none" />
        <path d="M29 16c-1.4-2 .6-3.4-.6-5" stroke="#8AADA0" stroke-width="2.4" stroke-linecap="round" fill="none" />
      </g>

      <!-- 小番茄 -->
      <g v-else-if="name === 'tomato'">
        <circle cx="24" cy="27" r="11" fill="#2F6B4F" />
        <circle cx="20.5" cy="23.5" r="3" fill="#8AADA0" opacity="0.7" />
        <path d="M24 16v-4M24 12c-1-3 0-4 0-4s1 1 0 4Z" stroke="#5d8d74" stroke-width="1.8" stroke-linecap="round" fill="none" />
      </g>

      <!-- 默认：小汤锅（兜底） -->
      <g v-else>
        <path d="M8 26a10 10 0 0 0 32 0 15 8 0 0 0-32 0Z" fill="#2F6B4F" />
        <path d="M10 25.5a13 7 0 0 0 28 0" fill="#E9F1EC" />
        <path d="M22 14c-1.4-2 .6-3.4-.6-5" stroke="#8AADA0" stroke-width="2.4" stroke-linecap="round" fill="none" />
        <path d="M30 13c-1.4-2 .6-3.4-.6-5" stroke="#8AADA0" stroke-width="2.4" stroke-linecap="round" fill="none" />
      </g>
    </template>
  </svg>
</template>

<script setup>
defineProps({
  name: { type: String, default: 'soup' },
  size: { type: [Number, String], default: 48 },
  line: { type: Boolean, default: false },
})
</script>
