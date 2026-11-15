import React, { useEffect, useRef } from 'react'

const ParticleNetwork = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    let W: number, H: number, DPR: number
    let particles: any[] = []
    let sparks: any[] = []
    let mouse = { x: 0, y: 0 }
    let smoothMouse = { x: 0, y: 0 }
    let animationFrameId: number

    const LAYERS = [
      { name: 'back', weight: 0.46, sizeMin: 0.6, sizeMax: 1.6, speedMin: 0.02, speedMax: 0.07,
        alphaMin: 0.15, alphaMax: 0.35, connect: false, linkDist: 0, glow: false, parallax: 3,
        shape: 'dot', hueMin: 178, hueMax: 205, sat: 45 },
      { name: 'mid', weight: 0.34, sizeMin: 2.0, sizeMax: 3.2, speedMin: 0.07, speedMax: 0.14,
        alphaMin: 0.35, alphaMax: 0.6, connect: true, linkDist: 105, linkBrightness: 0.32, glow: false, parallax: 9,
        shape: 'triangle', hueMin: 145, hueMax: 172, sat: 62 },
      { name: 'near', weight: 0.20, sizeMin: 3.6, sizeMax: 5.6, speedMin: 0.12, speedMax: 0.22,
        alphaMin: 0.55, alphaMax: 0.88, connect: true, linkDist: 165, linkBrightness: 0.55, glow: true, parallax: 20,
        shape: 'triangle', hueMin: 92, hueMax: 128, sat: 72 },
    ]

    function totalCount() {
      const area = window.innerWidth * window.innerHeight
      return Math.min(260, Math.max(70, Math.round(area / 9000)))
    }

    function makeParticle(layerIndex: number) {
      const layer = LAYERS[layerIndex]
      const angle = Math.random() * Math.PI * 2
      const speed = layer.speedMin + Math.random() * (layer.speedMax - layer.speedMin)
      return {
        layer: layerIndex,
        x: Math.random() * W,
        y: Math.random() * H,
        size: layer.sizeMin + Math.random() * (layer.sizeMax - layer.sizeMin),
        baseAlpha: layer.alphaMin + Math.random() * (layer.alphaMax - layer.alphaMin),
        hue: layer.hueMin + Math.random() * (layer.hueMax - layer.hueMin),
        sat: layer.sat + (Math.random() * 10 - 5),
        rotation: Math.random() * Math.PI * 2,
        rotSpeed: (Math.random() - 0.5) * 0.012,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        turnSeed: Math.random() * 1000,
        twinkleSeed: Math.random() * 1000,
        twinkleSpeed: 0.4 + Math.random() * 0.6,
      }
    }

    function buildParticles() {
      const total = totalCount()
      particles = []
      LAYERS.forEach((layer, i) => {
        const count = Math.round(total * layer.weight)
        for (let k = 0; k < count; k++) particles.push(makeParticle(i))
      })
    }

    let noisePattern: CanvasPattern | null = null
    function makeNoiseTexture() {
      const n = 128
      const off = document.createElement('canvas')
      off.width = n; off.height = n
      const octx = off.getContext('2d')
      if (!octx) return null
      const imgData = octx.createImageData(n, n)
      for (let i = 0; i < imgData.data.length; i += 4) {
        const v = Math.random() * 255
        imgData.data[i] = v
        imgData.data[i + 1] = v
        imgData.data[i + 2] = v
        imgData.data[i + 3] = Math.random() * 14
      }
      octx.putImageData(imgData, 0, 0)
      return ctx!.createPattern(off, 'repeat')
    }

    function resize() {
      DPR = Math.min(window.devicePixelRatio || 1, 2)
      const parent = canvas!.parentElement; W = parent ? parent.clientWidth : window.innerWidth;
      H = parent ? parent.clientHeight : window.innerHeight;
      canvas!.width = W * DPR
      canvas!.height = H * DPR
      // canvas!.style.width = '100%'
      // canvas!.style.height = '100%'
      ctx!.setTransform(DPR, 0, 0, DPR, 0, 0)
      buildParticles()
    }

    const onMouseMove = (e: MouseEvent) => {
      mouse.x = (e.clientX / W - 0.5) * 2
      mouse.y = (e.clientY / H - 0.5) * 2
    }

    const canvasParent = canvasRef.current?.parentElement; const ro = new ResizeObserver(resize); if (canvasParent) ro.observe(canvasParent); window.addEventListener('resize', resize)
    window.addEventListener('mousemove', onMouseMove)

    noisePattern = makeNoiseTexture()
    resize()

    function drawBackground(time: number) {
      const grad = ctx!.createRadialGradient(
        W * 0.22, H * 0.12, 0,
        W * 0.22, H * 0.12, Math.max(W, H) * 0.95
      )
      grad.addColorStop(0, '#2f6a3c')
      grad.addColorStop(0.22, '#1f5648')
      grad.addColorStop(0.45, '#123c4a')
      grad.addColorStop(0.68, '#0a2333')
      grad.addColorStop(1, '#040a16')
      ctx!.fillStyle = grad
      ctx!.fillRect(0, 0, W, H)

      if (!reduceMotion) {
        ctx!.save()
        ctx!.globalCompositeOperation = 'lighter'
        const blobs = [
          { x: W * (0.30 + 0.08 * Math.sin(time * 0.05)), y: H * (0.20 + 0.07 * Math.cos(time * 0.04)),
            r: H * 0.55, color: 'rgba(80,210,120,0.10)' },
          { x: W * (0.76 + 0.07 * Math.cos(time * 0.035 + 2)), y: H * (0.64 + 0.09 * Math.sin(time * 0.045 + 1)),
            r: H * 0.45, color: 'rgba(35,175,200,0.09)' },
          { x: W * (0.58 + 0.06 * Math.sin(time * 0.03 + 4)), y: H * (0.40 + 0.08 * Math.cos(time * 0.025 + 3)),
            r: H * 0.22, color: 'rgba(255,195,110,0.045)' },
        ]
        for (const b of blobs) {
          const g = ctx!.createRadialGradient(b.x, b.y, 0, b.x, b.y, b.r)
          g.addColorStop(0, b.color)
          g.addColorStop(1, 'rgba(0,0,0,0)')
          ctx!.fillStyle = g
          ctx!.fillRect(0, 0, W, H)
        }
        ctx!.restore()
      }

      ctx!.save()
      ctx!.globalAlpha = 0.55
      if (noisePattern) {
        ctx!.fillStyle = noisePattern
        ctx!.fillRect(0, 0, W, H)
      }
      ctx!.restore()

      const vig = ctx!.createRadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, H * 1.05)
      vig.addColorStop(0, 'rgba(0,0,0,0)')
      vig.addColorStop(1, 'rgba(6,4,16,0.55)')
      ctx!.fillStyle = vig
      ctx!.fillRect(0, 0, W, H)
    }

    function updateParticles(time: number, dt: number) {
      for (const p of particles) {
        const wobble = Math.sin(time * 0.15 + p.turnSeed) * 0.02
        const angle = Math.atan2(p.vy, p.vx) + wobble * dt * 60
        const speed = Math.hypot(p.vx, p.vy)
        p.vx = Math.cos(angle) * speed
        p.vy = Math.sin(angle) * speed

        p.x += p.vx * dt * 60
        p.y += p.vy * dt * 60
        p.rotation += p.rotSpeed * dt * 60

        if (p.x < -20) p.x = W + 20
        if (p.x > W + 20) p.x = -20
        if (p.y < -20) p.y = H + 20
        if (p.y > H + 20) p.y = -20
      }
    }

    function renderPos(p: any) {
      const layer = LAYERS[p.layer]
      return {
        x: p.x + smoothMouse.x * layer.parallax,
        y: p.y + smoothMouse.y * layer.parallax,
      }
    }

    function drawConnections(time: number, positions: any[]) {
      ctx!.lineWidth = 1
      const connectable = []
      for (let i = 0; i < particles.length; i++) {
        if (LAYERS[particles[i].layer].connect) connectable.push(i)
      }
      for (let i = 0; i < connectable.length; i++) {
        const ia = connectable[i]
        const a = particles[ia], pa = positions[ia]
        const la = LAYERS[a.layer]
        for (let j = i + 1; j < connectable.length; j++) {
          const ib = connectable[j]
          const b = particles[ib], pb = positions[ib]
          const lb = LAYERS[b.layer]
          const linkDist = (la.linkDist + lb.linkDist) / 2
          const dx = pa.x - pb.x, dy = pa.y - pb.y
          const dist = Math.hypot(dx, dy)
          if (dist < linkDist) {
            const brightness = ((la.linkBrightness || 0) + (lb.linkBrightness || 0)) / 2
            const alpha = (1 - dist / linkDist) * brightness
            const hue = (a.hue + b.hue) / 2
            ctx!.strokeStyle = `hsla(${hue.toFixed(0)}, 55%, 78%, ${alpha.toFixed(3)})`
            ctx!.beginPath()
            ctx!.moveTo(pa.x, pa.y)
            ctx!.lineTo(pb.x, pb.y)
            ctx!.stroke()
          }
        }
      }
      return connectable
    }

    function drawParticle(p: any, pos: any, time: number) {
      const layer = LAYERS[p.layer]
      const twinkle = 0.75 + 0.25 * Math.sin(time * p.twinkleSpeed + p.twinkleSeed)
      const alpha = p.baseAlpha * twinkle
      const hue = p.hue, sat = p.sat

      ctx!.save()
      if (layer.glow) {
        ctx!.shadowBlur = 8
        ctx!.shadowColor = `hsla(${hue.toFixed(0)}, ${sat.toFixed(0)}%, 75%, 0.9)`
      }

      if (layer.shape === 'dot') {
        ctx!.beginPath()
        ctx!.fillStyle = `hsla(${hue.toFixed(0)}, ${sat.toFixed(0)}%, 78%, ${alpha.toFixed(3)})`
        ctx!.arc(pos.x, pos.y, p.size, 0, Math.PI * 2)
        ctx!.fill()
      } else {
        const s = p.size
        ctx!.translate(pos.x, pos.y)
        ctx!.rotate(p.rotation)
        ctx!.beginPath()
        ctx!.moveTo(0, -s)
        ctx!.lineTo(s * 0.87, s * 0.5)
        ctx!.lineTo(-s * 0.87, s * 0.5)
        ctx!.closePath()
        ctx!.fillStyle = `hsla(${hue.toFixed(0)}, ${sat.toFixed(0)}%, 80%, ${(alpha * 0.7).toFixed(3)})`
        ctx!.fill()
        ctx!.strokeStyle = `hsla(${hue.toFixed(0)}, ${sat.toFixed(0)}%, 82%, ${alpha.toFixed(3)})`
        ctx!.lineWidth = 0.6
        ctx!.stroke()
      }
      ctx!.restore()
    }

    let sparkTimer = 0
    function maybeSpawnSpark(dt: number, positions: any[]) {
      sparkTimer -= dt
      if (sparkTimer > 0) return
      sparkTimer = 0.8 + Math.random() * 1.4

      const nearIdx = particles
        .map((p, i) => ({ p, i }))
        .filter(o => LAYERS[o.p.layer].name !== 'back')
      if (nearIdx.length < 2) return

      for (let attempt = 0; attempt < 6; attempt++) {
        const a = nearIdx[Math.floor(Math.random() * nearIdx.length)]
        const b = nearIdx[Math.floor(Math.random() * nearIdx.length)]
        if (a.i === b.i) continue
        const pa = positions[a.i], pb = positions[b.i]
        const dist = Math.hypot(pa.x - pb.x, pa.y - pb.y)
        const linkDist = (LAYERS[a.p.layer].linkDist + LAYERS[b.p.layer].linkDist) / 2
        if (dist < linkDist) {
          sparks.push({ ax: pa.x, ay: pa.y, bx: pb.x, by: pb.y, t: 0, duration: 0.7 + Math.random() * 0.5 })
          break
        }
      }
    }

    function easeInOut(t: number) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2 }

    function drawSparks(dt: number) {
      for (let i = sparks.length - 1; i >= 0; i--) {
        const s = sparks[i]
        s.t += dt / s.duration
        if (s.t >= 1) { sparks.splice(i, 1); continue }
        const e = easeInOut(s.t)
        const x = s.ax + (s.bx - s.ax) * e
        const y = s.ay + (s.by - s.ay) * e
        const fade = Math.sin(s.t * Math.PI)

        ctx!.save()
        ctx!.shadowBlur = 11
        ctx!.shadowColor = 'rgba(255,224,160,0.95)'
        ctx!.fillStyle = `rgba(255,238,200,${fade.toFixed(3)})`
        ctx!.beginPath()
        ctx!.arc(x, y, 1.8, 0, Math.PI * 2)
        ctx!.fill()
        ctx!.restore()
      }
    }

    let last = performance.now()

    function frame(now: number) {
      const time = now / 1000
      const dt = Math.min(0.05, (now - last) / 1000)
      last = now

      smoothMouse.x += (mouse.x - smoothMouse.x) * 0.05
      smoothMouse.y += (mouse.y - smoothMouse.y) * 0.05

      drawBackground(time)
      updateParticles(time, dt)

      const positions = particles.map(renderPos)
      drawConnections(time, positions)

      for (let i = 0; i < particles.length; i++) drawParticle(particles[i], positions[i], time)

      if (!reduceMotion) {
        maybeSpawnSpark(dt, positions)
        drawSparks(dt)
      }

      animationFrameId = requestAnimationFrame(frame)
    }

    animationFrameId = requestAnimationFrame(frame)

    return () => {
      ro.disconnect(); window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', onMouseMove)
      cancelAnimationFrame(animationFrameId)
    }
  }, [])

  return (
    <canvas 
      ref={canvasRef} 
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        display: 'block',
        pointerEvents: 'none',
        zIndex: 0
      }} 
    />
  )
}

export default ParticleNetwork
