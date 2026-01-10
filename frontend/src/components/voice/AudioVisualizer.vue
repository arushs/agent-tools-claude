<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'

const props = defineProps<{
  isActive: boolean
  getAudioData: () => Uint8Array
  barCount?: number
  color?: string
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
let animationId: number | null = null

const barCount = props.barCount ?? 32
const barColor = props.color ?? '#3b82f6'

function draw() {
  const canvas = canvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const audioData = props.getAudioData()
  const width = canvas.width
  const height = canvas.height

  // Clear canvas
  ctx.clearRect(0, 0, width, height)

  if (audioData.length === 0) {
    // Draw idle state - small bars
    drawIdleBars(ctx, width, height)
    return
  }

  // Calculate bar dimensions
  const barWidth = width / barCount
  const gap = 2
  const effectiveBarWidth = barWidth - gap

  // Sample audio data evenly
  const step = Math.floor(audioData.length / barCount)

  for (let i = 0; i < barCount; i++) {
    const dataIndex = i * step
    const value = audioData[dataIndex] ?? 0

    // Normalize value (0-255) to height
    const barHeight = (value / 255) * height * 0.9 + height * 0.1

    // Calculate position (centered)
    const x = i * barWidth + gap / 2
    const y = (height - barHeight) / 2

    // Draw bar with rounded corners
    ctx.fillStyle = barColor
    ctx.beginPath()
    const radius = Math.min(effectiveBarWidth / 2, 4)
    roundedRect(ctx, x, y, effectiveBarWidth, barHeight, radius)
    ctx.fill()
  }

  if (props.isActive) {
    animationId = requestAnimationFrame(draw)
  }
}

function drawIdleBars(ctx: CanvasRenderingContext2D, width: number, height: number) {
  const barWidth = width / barCount
  const gap = 2
  const effectiveBarWidth = barWidth - gap
  const minHeight = 4

  for (let i = 0; i < barCount; i++) {
    const x = i * barWidth + gap / 2
    const y = (height - minHeight) / 2

    ctx.fillStyle = '#d1d5db' // gray-300
    ctx.beginPath()
    const radius = Math.min(effectiveBarWidth / 2, 2)
    roundedRect(ctx, x, y, effectiveBarWidth, minHeight, radius)
    ctx.fill()
  }
}

function roundedRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number
) {
  ctx.moveTo(x + radius, y)
  ctx.lineTo(x + width - radius, y)
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius)
  ctx.lineTo(x + width, y + height - radius)
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
  ctx.lineTo(x + radius, y + height)
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius)
  ctx.lineTo(x, y + radius)
  ctx.quadraticCurveTo(x, y, x + radius, y)
}

function startAnimation() {
  if (animationId !== null) return
  animationId = requestAnimationFrame(draw)
}

function stopAnimation() {
  if (animationId !== null) {
    cancelAnimationFrame(animationId)
    animationId = null
  }

  // Draw idle state
  const canvas = canvasRef.value
  if (canvas) {
    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      drawIdleBars(ctx, canvas.width, canvas.height)
    }
  }
}

watch(
  () => props.isActive,
  (isActive) => {
    if (isActive) {
      startAnimation()
    } else {
      stopAnimation()
    }
  },
  { immediate: true }
)

onUnmounted(() => {
  stopAnimation()
})
</script>

<template>
  <canvas
    ref="canvasRef"
    class="w-full h-12"
    width="256"
    height="48"
  />
</template>
