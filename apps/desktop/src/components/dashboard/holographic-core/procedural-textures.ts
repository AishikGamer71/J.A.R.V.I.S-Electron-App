import * as THREE from 'three'
import type { ProceduralTextures } from './types'

/**
 * Creates a procedural 64x64 radial glow CanvasTexture for the volumetric core
 * and particle point sprites.
 */
export function createVolumetricGlowTexture(): THREE.CanvasTexture {
  const gSize = 64
  const gCanvas = document.createElement('canvas')
  gCanvas.width = gSize
  gCanvas.height = gSize
  const gCtx = gCanvas.getContext('2d')
  if (gCtx) {
    const half = gSize / 2
    const grad = gCtx.createRadialGradient(half, half, 0, half, half, half)
    grad.addColorStop(0, 'rgba(255, 255, 255, 1)')
    grad.addColorStop(0.22, 'rgba(255, 255, 255, 0.86)')
    grad.addColorStop(0.55, 'rgba(255, 255, 255, 0.22)')
    grad.addColorStop(1, 'rgba(255, 255, 255, 0)')
    gCtx.fillStyle = grad
    gCtx.fillRect(0, 0, gSize, gSize)
  }
  const texture = new THREE.CanvasTexture(gCanvas)
  texture.needsUpdate = true
  return texture
}

/**
 * Creates a procedural 128x128 dark navy contrast backdrop CanvasTexture
 * acting as an optical billboard behind the holographic core.
 */
export function createBackdropHaloTexture(): THREE.CanvasTexture {
  const bSize = 128
  const bCanvas = document.createElement('canvas')
  bCanvas.width = bSize
  bCanvas.height = bSize
  const bCtx = bCanvas.getContext('2d')
  if (bCtx) {
    const half = bSize / 2
    const bGrad = bCtx.createRadialGradient(half, half, 0, half, half, half)
    bGrad.addColorStop(0, 'rgba(2, 8, 22, 0.88)')
    bGrad.addColorStop(0.48, 'rgba(3, 12, 28, 0.70)')
    bGrad.addColorStop(0.76, 'rgba(3, 12, 28, 0.24)')
    bGrad.addColorStop(1, 'rgba(0, 0, 0, 0)')
    bCtx.fillStyle = bGrad
    bCtx.fillRect(0, 0, bSize, bSize)
  }
  const texture = new THREE.CanvasTexture(bCanvas)
  texture.needsUpdate = true
  return texture
}

/**
 * Convenience factory to create both procedural textures simultaneously.
 */
export function createProceduralTextures(): ProceduralTextures {
  return {
    glowTexture: createVolumetricGlowTexture(),
    backdropTexture: createBackdropHaloTexture(),
  }
}

/**
 * Releases GPU resources associated with the procedural CanvasTextures.
 */
export function disposeProceduralTextures(textures: ProceduralTextures | null | undefined): void {
  if (!textures) return
  if (textures.glowTexture) {
    textures.glowTexture.dispose()
  }
  if (textures.backdropTexture) {
    textures.backdropTexture.dispose()
  }
}
