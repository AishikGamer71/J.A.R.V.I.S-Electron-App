import * as THREE from 'three'
import {
  BASE_RADIUS,
  DEFAULT_PARTICLE_COUNT,
  RING1_CONFIG,
  RING2_CONFIG,
  RING3_CONFIG,
} from './constants'
import type { ParticleGeometryData } from './types'

/**
 * Generates uniformly distributed 3D Fibonacci sphere vertices with precomputed
 * morph targets (quantized lat/lon globe and beveled holo-cube) and stochastic seeds.
 */
export function buildParticleGeometryData(
  count: number = DEFAULT_PARTICLE_COUNT,
  baseRadius: number = BASE_RADIUS
): ParticleGeometryData {
  const pos = new Float32Array(count * 3)
  const col = new Float32Array(count * 3)
  const norm = new Float32Array(count * 3)
  const globe = new Float32Array(count * 3)
  const cube = new Float32Array(count * 3)
  const thArr = new Float32Array(count)
  const phArr = new Float32Array(count)
  const phaseArr = new Float32Array(count)
  const spreadArr = new Float32Array(count)
  const seedArr = new Float32Array(count)

  const goldenAngle = Math.PI * (3 - Math.sqrt(5))

  for (let i = 0; i < count; i++) {
    const y = 1 - (i / Math.max(1, count - 1)) * 2
    const rAtY = Math.sqrt(Math.max(0, 1 - y * y))
    const th = goldenAngle * i

    // Fibonacci sphere with subtle organic micro-jitter (preventing polar moiré patterns)
    let nx = Math.cos(th) * rAtY + (Math.random() - 0.5) * 0.025
    let ny = y + (Math.random() - 0.5) * 0.025
    let nz = Math.sin(th) * rAtY + (Math.random() - 0.5) * 0.025
    const len = Math.hypot(nx, ny, nz) || 1
    nx /= len
    ny /= len
    nz /= len

    const ix = i * 3
    norm[ix] = nx
    norm[ix + 1] = ny
    norm[ix + 2] = nz

    pos[ix] = nx * baseRadius
    pos[ix + 1] = ny * baseRadius
    pos[ix + 2] = nz * baseRadius

    // Base Ice-Cyan color
    col[ix] = 0.4
    col[ix + 1] = 0.91
    col[ix + 2] = 0.98

    const theta = Math.atan2(nz, nx)
    const phi = Math.acos(Math.max(-1, Math.min(1, ny)))
    thArr[i] = theta
    phArr[i] = phi
    phaseArr[i] = Math.random() * Math.PI * 2
    spreadArr[i] = Math.random()

    // 1. Lat/Lon Hologram Globe Morph Target (WEB_SEARCH)
    let gTheta = theta
    let gPhi = phi
    if (i % 2 === 0) {
      // 12 Longitudinal Meridians
      const meridians = 12
      gTheta = Math.round(theta / ((Math.PI * 2) / meridians)) * ((Math.PI * 2) / meridians)
    } else {
      // 8 Latitudinal Parallels
      const parallels = 8
      gPhi = Math.max(
        0.16,
        Math.min(Math.PI - 0.16, Math.round(phi / (Math.PI / parallels)) * (Math.PI / parallels))
      )
    }
    const gx = Math.sin(gPhi) * Math.cos(gTheta)
    const gy = Math.cos(gPhi)
    const gz = Math.sin(gPhi) * Math.sin(gTheta)
    globe[ix] = nx * 0.18 + gx * 0.82
    globe[ix + 1] = ny * 0.18 + gy * 0.82
    globe[ix + 2] = nz * 0.18 + gz * 0.82

    // 2. Beveled 3D Holo-Cube Morph Target (CODING)
    const maxAxis = Math.max(Math.abs(nx), Math.abs(ny), Math.abs(nz)) || 1
    const cx = (nx / maxAxis) * 0.77
    const cy = (ny / maxAxis) * 0.77
    const cz = (nz / maxAxis) * 0.77
    cube[ix] = nx * 0.16 + cx * 0.84
    cube[ix + 1] = ny * 0.16 + cy * 0.84
    cube[ix + 2] = nz * 0.16 + cz * 0.84

    // Deterministic matrix rain column seeds
    const qx = Math.round(cx * 5) + 10
    const qz = Math.round(cz * 5) + 10
    seedArr[i] = ((qx * 37 + qz * 17) % 19) * 0.55
  }

  return {
    positions: pos,
    colors: col,
    normals: norm,
    globeNormals: globe,
    cubeNormals: cube,
    thetas: thArr,
    phis: phArr,
    phases: phaseArr,
    spreads: spreadArr,
    colSeeds: seedArr,
  }
}

/**
 * Creates TorusGeometry instances for the three gyroscopic rings.
 */
export function createRingGeometries(): {
  ring1Geom: THREE.TorusGeometry
  ring2Geom: THREE.TorusGeometry
  ring3Geom: THREE.TorusGeometry
} {
  return {
    ring1Geom: new THREE.TorusGeometry(
      RING1_CONFIG.radius,
      RING1_CONFIG.tube,
      RING1_CONFIG.radialSegments,
      RING1_CONFIG.tubularSegments
    ),
    ring2Geom: new THREE.TorusGeometry(
      RING2_CONFIG.radius,
      RING2_CONFIG.tube,
      RING2_CONFIG.radialSegments,
      RING2_CONFIG.tubularSegments
    ),
    ring3Geom: new THREE.TorusGeometry(
      RING3_CONFIG.radius,
      RING3_CONFIG.tube,
      RING3_CONFIG.radialSegments,
      RING3_CONFIG.tubularSegments
    ),
  }
}

/**
 * Disposes ring geometries cleanly.
 */
export function disposeRingGeometries(geometries?: {
  ring1Geom?: THREE.TorusGeometry
  ring2Geom?: THREE.TorusGeometry
  ring3Geom?: THREE.TorusGeometry
}): void {
  if (!geometries) return
  geometries.ring1Geom?.dispose()
  geometries.ring2Geom?.dispose()
  geometries.ring3Geom?.dispose()
}
