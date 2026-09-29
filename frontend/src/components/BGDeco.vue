<template>
  <!-- 页面背景装饰：手绘涂鸦线条散落层（大尺寸，铺在内容区空白处） -->
  <div class="bg-deco" aria-hidden="true">
    <FoodIcons name="chef" :size="160" line class="d d1" />
    <FoodIcons name="pot" :size="170" line class="d d2" />
    <FoodIcons name="fish" :size="140" line class="d d3" />
    <FoodIcons name="teapot" :size="130" line class="d d4" />
    <FoodIcons name="bread" :size="150" line class="d d5" />
    <FoodIcons name="spatula" :size="120" line class="d d6" />
    <FoodIcons name="apple" :size="110" line class="d d7" />
    <FoodIcons name="strawberry" :size="100" line class="d d8" />
    <FoodIcons name="carrot" :size="115" line class="d d9" />
    <FoodIcons name="broccoli" :size="125" line class="d d10" />
    <FoodIcons name="milk" :size="105" line class="d d11" />
    <FoodIcons name="egg" :size="95" line class="d d12" />
    <FoodIcons name="ladle" :size="110" line class="d d13" />
    <FoodIcons name="knife" :size="130" line class="d d14" />
    <FoodIcons name="soup" :size="150" line class="d d15" />
    <FoodIcons name="orange" :size="100" line class="d d16" />
    <FoodIcons name="pan" :size="120" line class="d d17" />
    <!-- 甜点咖啡组 -->
      <FoodIcons name="cupcake" :size="118" line class="d d26" />
      <FoodIcons name="croissant" :size="112" line class="d d27" />
      <FoodIcons name="baguette" :size="124" line class="d d28" />
      <FoodIcons name="pretzel" :size="106" line class="d d29" />
      <FoodIcons name="cheese" :size="108" line class="d d30" />
      <FoodIcons name="donut" :size="100" line class="d d31" />
      <FoodIcons name="coffee" :size="114" line class="d d32" />
      <FoodIcons name="whisk" :size="96" line class="d d33" />
      <FoodIcons name="sandwich" :size="118" line class="d d34" />
      <FoodIcons name="cocktail" :size="104" line class="d d35" />

      <!-- 爱心 / 枝叶 / 加号 / 星点 点缀 -->
      <FoodIcons name="heart" :size="40" line class="d d18" />
    <FoodIcons name="heart" :size="36" line class="d d19" />
    <FoodIcons name="leaf" :size="70" line class="d d20" />
    <FoodIcons name="leaf" :size="56" line class="d d21" />
    <FoodIcons name="plus" :size="40" line class="d d22" />
    <FoodIcons name="plus" :size="30" line class="d d23" />
    <FoodIcons name="star" :size="36" line class="d d24" />
    <FoodIcons name="star" :size="28" line class="d d25" />
      <FoodIcons name="heart" :size="34" line class="d d36" />
      <FoodIcons name="star" :size="30" line class="d d37" />
      <FoodIcons name="plus" :size="34" line class="d d38" />
      <FoodIcons name="leaf" :size="60" line class="d d39" />
  </div>
</template>

<script setup>
import FoodIcons from './FoodIcons.vue'
</script>

<style scoped>
.bg-deco {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}
.d {
  position: absolute;
  opacity: 0.22;
}
/* 铺在大面积空白处：顶部标题区、中部两侧、底部 */
.d1  { top: 5%;   left: 5%;    transform: rotate(-8deg); }
.d2  { top: 12%;  right: 6%;   transform: rotate(6deg); }
.d3  { top: 38%;  left: 7%;    transform: rotate(-12deg); }
.d4  { top: 45%;  right: 5%;   transform: rotate(10deg); }
.d5  { top: 72%;  left: 34%;   transform: rotate(4deg); }
.d6  { top: 63%;  left: 3%;    transform: rotate(15deg); }
.d7  { top: 74%;  right: 9%;   transform: rotate(-8deg); }
.d8  { top: 2%;   left: 30%;   transform: rotate(20deg); }
.d9  { top: 4%;   right: 26%;  transform: rotate(-10deg); }
.d10 { top: 28%;  left: 2%;    transform: rotate(6deg); }
.d11 { top: 30%;  right: 2.5%; transform: rotate(-6deg); }
.d12 { top: 86%;  left: 24%;   transform: rotate(-14deg); }
.d13 { top: 16%;  left: 20%;   transform: rotate(9deg); }
.d14 { top: 56%;  right: 14%;  transform: rotate(12deg); }
.d15 { top: 84%;  right: 22%;  transform: rotate(-5deg); }
.d16 { top: 82%;  right: 42%;  transform: rotate(7deg); }
.d17 { top: 62%;  left: 40%;   transform: rotate(-6deg); }
.d18 { top: 20%;  right: 32%;  transform: rotate(-12deg); }
.d19 { top: 66%;  left: 16%;   transform: rotate(10deg); }
.d20 { top: 9%;   right: 18%;  transform: rotate(-15deg); }
.d21 { top: 52%;  left: 30%;   transform: rotate(18deg); }
.d22 { top: 33%;  right: 24%;  transform: rotate(-20deg); }
.d23 { top: 76%;  left: 6%;    transform: rotate(15deg); }
.d24 { top: 12%;  left: 55%;   transform: rotate(-8deg); }
.d25 { top: 48%; right: 33%; transform: rotate(30deg); }
.d26 { top: 22%; left: 44%; transform: rotate(-6deg); }
.d27 { top: 8%; left: 66%; transform: rotate(8deg); }
.d28 { top: 60%; left: 54%; transform: rotate(-14deg); }
.d29 { top: 40%; left: 47%; transform: rotate(5deg); }
.d30 { top: 26%; right: 14%; transform: rotate(-9deg); }
.d31 { top: 78%; left: 50%; transform: rotate(12deg); }
.d32 { top: 88%; left: 8%; transform: rotate(-5deg); }
.d33 { top: 34%; right: 40%; transform: rotate(15deg); }
.d34 { top: 86%; right: 8%; transform: rotate(6deg); }
.d35 { top: 50%; left: 20%; transform: rotate(-7deg); }
.d36 { top: 18%; left: 57%; transform: rotate(10deg); }
.d37 { top: 44%; right: 20%; transform: rotate(-12deg); }
.d38 { top: 70%; right: 28%; transform: rotate(8deg); }
.d39 { top: 57%; right: 7%; transform: rotate(-18deg); }
</style>
