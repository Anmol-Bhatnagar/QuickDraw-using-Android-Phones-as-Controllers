/*
 * Tilt Maze - Phone Tilt Ball Physics Game.
 *
 * Inspired by Neilfal/phone-controller:
 * - Tilt the phone to roll your marble across the arena table.
 * - Tap JUMP or shake the phone to hop over red hazard pits.
 * - Collect glowing yellow stars to score points.
 * - Falling into a hazard pit costs points and resets your marble.
 * - Supports 1 or 2 players simultaneously with distinct marbles and scores.
 */

import * as THREE from "../../lib/three.module.js";
import { addLights, skyDome, clamp, damp, lerp } from "../arena.js";
import { sfx } from "../audio.js";

const TABLE_W = 14;          // arena half-width (X: -14 to +14)
const TABLE_L = 10;          // arena half-length (Z: -10 to +10)
const BALL_R = 0.55;
const ACCEL_FORCE = 32.0;    // physics acceleration from tilt
const DRAG = 0.05;           // friction / drag per second
const MAX_SPEED = 18.0;
const BOUNCE_RESTITUTION = 0.65;
const JUMP_DURATION = 0.62;   // seconds
const JUMP_PEAK_H = 1.4;     // vertical height

// Pre-defined hazard pit locations [x, z, radius]
const PITS_CONFIG = [
  [-7.0, -4.5, 1.25],
  [7.0, -4.5, 1.25],
  [-7.0, 4.5, 1.25],
  [7.0, 4.5, 1.25],
  [0.0, -3.2, 1.35],
  [0.0, 3.2, 1.35],
  [-4.0, 0.0, 1.2],
  [4.0, 0.0, 1.2],
];

// Inner maze bumpers/walls [x, z, halfW, halfD]
const BUMPERS = [
  [-3.5, -6.5, 0.35, 1.8],
  [3.5, -6.5, 0.35, 1.8],
  [-3.5, 6.5, 0.35, 1.8],
  [3.5, 6.5, 0.35, 1.8],
  [-9.5, 0.0, 0.35, 2.5],
  [9.5, 0.0, 0.35, 2.5],
];

export class TiltMazeGame {
  constructor(ctx) {
    this.ctx = ctx;
    this.name = "Tilt Maze";
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(48, 16 / 9, 0.1, 100);
    this.cameras = [this.camera];

    this.players = [];
    this.star = null;
    this.starMesh = null;
    this.pits = [];
    this.particles = [];
    this.roundTime = 60; // 60s rounds
    this.timeLeft = 60;
    this.gameOver = false;

    this._build();
  }

  _build() {
    const scene = this.scene;
    scene.add(skyDome(0x0e172a, 0x1e293b));
    addLights(scene, {
      sky: 0x93c5fd,
      ground: 0x1e293b,
      ambient: 1.1,
      sun: 1.4,
      shadowRange: 18,
    });

    // Accent overhead point lights
    const lamp1 = new THREE.PointLight(0x38bdf8, 2.5, 25);
    lamp1.position.set(-6, 8, -4);
    scene.add(lamp1);

    const lamp2 = new THREE.PointLight(0xfbbf24, 2.5, 25);
    lamp2.position.set(6, 8, 4);
    scene.add(lamp2);

    // Table bed / floor
    const floorGeo = new THREE.BoxGeometry(TABLE_W * 2, 0.6, TABLE_L * 2);
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      roughness: 0.35,
      metalness: 0.25,
    });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.position.y = -0.3;
    floor.receiveShadow = true;
    scene.add(floor);

    // Grid markings on the table
    const grid = new THREE.GridHelper(TABLE_W * 2, 28, 0x38bdf8, 0x334155);
    grid.position.y = 0.01;
    scene.add(grid);

    // Wooden / neon outer borders
    const rimMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      roughness: 0.2,
      metalness: 0.6,
    });
    const glowMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 });

    // North & South walls
    const nsGeo = new THREE.BoxGeometry(TABLE_W * 2 + 0.8, 1.0, 0.4);
    const wallN = new THREE.Mesh(nsGeo, rimMat);
    wallN.position.set(0, 0.5, -(TABLE_L + 0.2));
    wallN.castShadow = true;
    scene.add(wallN);

    const wallS = new THREE.Mesh(nsGeo, rimMat);
    wallS.position.set(0, 0.5, TABLE_L + 0.2);
    wallS.castShadow = true;
    scene.add(wallS);

    // East & West walls
    const ewGeo = new THREE.BoxGeometry(0.4, 1.0, TABLE_L * 2);
    const wallE = new THREE.Mesh(ewGeo, rimMat);
    wallE.position.set(TABLE_W + 0.2, 0.5, 0);
    wallE.castShadow = true;
    scene.add(wallE);

    const wallW = new THREE.Mesh(ewGeo, rimMat);
    wallW.position.set(-(TABLE_W + 0.2), 0.5, 0);
    wallW.castShadow = true;
    scene.add(wallW);

    // Inner obstacle bumpers
    const bumperMat = new THREE.MeshStandardMaterial({
      color: 0x475569,
      roughness: 0.3,
      metalness: 0.5,
    });
    this.bumperMeshes = [];
    for (const b of BUMPERS) {
      const geo = new THREE.BoxGeometry(b[2] * 2, 0.8, b[3] * 2);
      const mesh = new THREE.Mesh(geo, bumperMat);
      mesh.position.set(b[0], 0.4, b[1]);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      scene.add(mesh);
      this.bumperMeshes.push({ x: b[0], z: b[1], hw: b[2], hd: b[3], mesh });
    }

    // Hazard Pits
    this.pits = [];
    const pitGeo = new THREE.CylinderGeometry(1, 1, 0.1, 28);
    const pitMat = new THREE.MeshBasicMaterial({ color: 0xef4444 });
    const pitInnerMat = new THREE.MeshBasicMaterial({ color: 0x450a0a });

    for (const p of PITS_CONFIG) {
      const [px, pz, pr] = p;
      const group = new THREE.Group();
      group.position.set(px, 0.02, pz);

      // Warning hazard ring
      const ringGeo = new THREE.RingGeometry(pr * 0.95, pr * 1.08, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0xef4444,
        side: THREE.DoubleSide,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = -Math.PI / 2;
      group.add(ring);

      // Deep dark pit hole
      const hole = new THREE.Mesh(
        new THREE.CircleGeometry(pr * 0.95, 32),
        pitInnerMat
      );
      hole.rotation.x = -Math.PI / 2;
      group.add(hole);

      scene.add(group);
      this.pits.push({ x: px, z: pz, r: pr, group });
    }

    // Collectible Star (glowing golden 3D octahedron/star combo)
    const starGroup = new THREE.Group();
    const starCore = new THREE.Mesh(
      new THREE.OctahedronGeometry(0.7, 0),
      new THREE.MeshStandardMaterial({
        color: 0xfacc15,
        emissive: 0xf59e0b,
        emissiveIntensity: 0.8,
        roughness: 0.2,
        metalness: 0.8,
      })
    );
    starCore.castShadow = true;
    starGroup.add(starCore);

    // Glowing halo ring
    const starHalo = new THREE.Mesh(
      new THREE.TorusGeometry(0.85, 0.08, 8, 24),
      new THREE.MeshBasicMaterial({ color: 0xfde047 })
    );
    starHalo.rotation.x = Math.PI / 2;
    starGroup.add(starHalo);

    const starLight = new THREE.PointLight(0xfacc15, 3.0, 6.0);
    starGroup.add(starLight);

    starGroup.position.set(0, 0.85, 0);
    scene.add(starGroup);
    this.starMesh = starGroup;
    this.star = { x: 0, z: 0, r: 0.75 };
    this._respawnStar();

    // Camera overhead angled view
    this.camera.position.set(0, 19.5, 14.5);
    this.camera.lookAt(0, 0, 0);

    // Particle pool for star collections
    this._initParticles();
  }

  _initParticles() {
    this.particleGroup = new THREE.Group();
    this.scene.add(this.particleGroup);
    this.particlePool = [];
    const pGeo = new THREE.SphereGeometry(0.12, 6, 6);
    const pMat = new THREE.MeshBasicMaterial({ color: 0xfde047 });
    for (let i = 0; i < 40; i++) {
      const p = new THREE.Mesh(pGeo, pMat);
      p.visible = false;
      this.particleGroup.add(p);
      this.particlePool.push({
        mesh: p,
        vx: 0,
        vy: 0,
        vz: 0,
        life: 0,
        maxLife: 1,
      });
    }
  }

  _spawnSparks(x, y, z, color = 0xfde047) {
    let count = 0;
    for (const p of this.particlePool) {
      if (!p.mesh.visible) {
        p.mesh.visible = true;
        p.mesh.position.set(x, y, z);
        p.mesh.material.color.setHex(color);
        const spd = 2.0 + Math.random() * 4.0;
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.random() * Math.PI;
        p.vx = Math.sin(phi) * Math.cos(theta) * spd;
        p.vy = Math.cos(phi) * spd + 2.0;
        p.vz = Math.sin(phi) * Math.sin(theta) * spd;
        p.life = 0.5 + Math.random() * 0.4;
        p.maxLife = p.life;
        count++;
        if (count >= 16) break;
      }
    }
  }

  _createPlayer(seatIdx, pid, colorHex, label) {
    const group = new THREE.Group();

    // Metallic marble sphere
    const sphereMat = new THREE.MeshStandardMaterial({
      color: colorHex,
      roughness: 0.15,
      metalness: 0.85,
    });
    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(BALL_R, 24, 18),
      sphereMat
    );
    sphere.castShadow = true;
    group.add(sphere);

    // Shadow decal that stays flat on the table
    const shadowGeo = new THREE.CircleGeometry(BALL_R * 1.15, 20);
    const shadowMat = new THREE.MeshBasicMaterial({
      color: 0x000000,
      transparent: true,
      opacity: 0.45,
    });
    const shadow = new THREE.Mesh(shadowGeo, shadowMat);
    shadow.rotation.x = -Math.PI / 2;
    shadow.position.y = 0.02;
    this.scene.add(shadow);

    this.scene.add(group);

    return {
      seat: seatIdx,
      pid: pid,
      label: label,
      color: colorHex,
      group: group,
      sphere: sphere,
      shadow: shadow,
      x: seatIdx === 0 ? -4.0 : 4.0,
      z: 0.0,
      vx: 0.0,
      vz: 0.0,
      jumpT: 0.0,
      jumpHeight: 0.0,
      score: 0,
      falling: false,
      fallT: 0.0,
      lastSpeed: 0,
    };
  }

  enter() {
    this.timeLeft = 60;
    this.gameOver = false;

    // Remove old player meshes
    for (const p of this.players) {
      this.scene.remove(p.group);
      this.scene.remove(p.shadow);
    }
    this.players = [];

    // Determine connected controllers
    const c1 = this.ctx.seat(0) || this.ctx.controllers.first();
    const c2 = this.ctx.seat(1);

    this.players.push(
      this._createPlayer(0, c1 ? c1.pid : 1, 0x38bdf8, "P1")
    );

    if (c2 && c2.pid !== (c1 ? c1.pid : 1)) {
      this.players.push(
        this._createPlayer(1, c2.pid, 0xf97316, "P2")
      );
    }

    // Reset ball positions
    this._resetBall(this.players[0], -4.0, 0.0);
    if (this.players[1]) {
      this._resetBall(this.players[1], 4.0, 0.0);
    }

    this._respawnStar();
    this._updateHud();

    // Broadcast controller mode to phones
    this.ctx.net.mode(
      0,
      "Tilt Maze",
      "Tilt phone to roll ball. Shake or tap JUMP to hop pits!",
      "JUMP",
      "Hop over hazard pits"
    );
  }

  exit() {
    for (const p of this.players) {
      this.scene.remove(p.group);
      this.scene.remove(p.shadow);
    }
    this.players = [];
  }

  onCalibrate(pid) {
    const p = this.players.find((pl) => pl.pid === pid);
    if (p) {
      p.vx = 0;
      p.vz = 0;
      this.ctx.ui.toast("CALIBRATED", p.label + " neutral tilt zeroed", 900);
      sfx.tone(440, 0.08, { gain: 0.1 });
    }
  }

  onButton(down, pid, key) {
    if (!down) return;
    const p = this.players.find((pl) => pl.pid === pid) || this.players[0];
    if (p) {
      this._triggerJump(p);
    }
  }

  _triggerJump(p) {
    if (p.falling || p.jumpT > 0) return;
    p.jumpT = JUMP_DURATION;
    sfx.whoosh();
    this.ctx.net.buzz(p.pid, 30);
  }

  _resetBall(p, x, z) {
    p.x = x;
    p.z = z;
    p.vx = 0;
    p.vz = 0;
    p.jumpT = 0;
    p.jumpHeight = 0;
    p.falling = false;
    p.fallT = 0;
    p.group.scale.set(1, 1, 1);
    p.group.position.set(p.x, BALL_R, p.z);
    p.shadow.position.set(p.x, 0.02, p.z);
    p.shadow.visible = true;
  }

  _respawnStar() {
    let bestX = 0,
      bestZ = 0,
      found = false;
    for (let attempts = 0; attempts < 30; attempts++) {
      const rx = (Math.random() * 2 - 1) * (TABLE_W - 2.5);
      const rz = (Math.random() * 2 - 1) * (TABLE_L - 2.5);

      // Check distance from all pits
      let safe = true;
      for (const pit of this.pits) {
        const dx = rx - pit.x;
        const dz = rz - pit.z;
        if (Math.hypot(dx, dz) < pit.r + 1.6) {
          safe = false;
          break;
        }
      }
      if (safe) {
        bestX = rx;
        bestZ = rz;
        found = true;
        break;
      }
    }
    if (!found) {
      bestX = (Math.random() - 0.5) * 8;
      bestZ = (Math.random() - 0.5) * 6;
    }
    this.star.x = bestX;
    this.star.z = bestZ;
    this.starMesh.position.set(bestX, 0.85, bestZ);
  }

  update(dt, now) {
    if (!this.gameOver) {
      this.timeLeft -= dt;
      if (this.timeLeft <= 0) {
        this.timeLeft = 0;
        this.gameOver = true;
        this._endGame();
      }
    }

    // Animate star rotation and floating bob
    if (this.starMesh) {
      this.starMesh.rotation.y += dt * 2.2;
      this.starMesh.position.y = 0.85 + Math.sin(now * 3.5) * 0.18;
    }

    // Update particles
    for (const p of this.particlePool) {
      if (p.mesh.visible) {
        p.life -= dt;
        if (p.life <= 0) {
          p.mesh.visible = false;
        } else {
          p.mesh.position.x += p.vx * dt;
          p.mesh.position.y += p.vy * dt;
          p.mesh.position.z += p.vz * dt;
          p.vy -= 9.8 * dt; // gravity
          const scale = p.life / p.maxLife;
          p.mesh.scale.set(scale, scale, scale);
        }
      }
    }

    // Process each player
    for (let i = 0; i < this.players.length; i++) {
      const p = this.players[i];
      const ctrl = this.ctx.seat(i) || (i === 0 ? this.ctx.controllers.first() : null);

      this._updatePlayer(p, ctrl, dt, now);
    }

    this._updateHud();
  }

  _updatePlayer(p, ctrl, dt, now) {
    // If player is falling into a pit
    if (p.falling) {
      p.fallT += dt;
      const s = Math.max(0.01, 1.0 - p.fallT * 2.5);
      p.group.scale.set(s, s, s);
      p.group.position.y -= dt * 3.5;
      p.shadow.visible = false;

      if (p.fallT > 0.65) {
        // Reset to safe starting side
        const resetX = p.seat === 0 ? -4.0 : 4.0;
        this._resetBall(p, resetX, 0.0);
      }
      return;
    }

    // Input tilt
    let ax = 0;
    let az = 0;
    if (ctrl) {
      // aim is roll (left/right X), lean is pitch (forward/back Z)
      ax = clamp(ctrl.aim, -1.0, 1.0);
      az = clamp(ctrl.lean, -1.0, 1.0);

      // Shake detection: sudden motion spikes jump
      if (ctrl.speed > 14.0 && p.lastSpeed <= 14.0) {
        this._triggerJump(p);
      }
      p.lastSpeed = ctrl.speed;
    }

    // Accelerate ball
    p.vx += ax * ACCEL_FORCE * dt;
    p.vz += az * ACCEL_FORCE * dt;

    // Apply drag/friction
    const frictionFactor = Math.pow(DRAG, dt);
    p.vx *= frictionFactor;
    p.vz *= frictionFactor;

    // Cap maximum speed
    const spd = Math.hypot(p.vx, p.vz);
    if (spd > MAX_SPEED) {
      p.vx = (p.vx / spd) * MAX_SPEED;
      p.vz = (p.vz / spd) * MAX_SPEED;
    }

    // Handle Jump / Hop physics
    if (p.jumpT > 0) {
      p.jumpT -= dt;
      const progress = 1.0 - Math.max(0, p.jumpT / JUMP_DURATION);
      p.jumpHeight = Math.sin(progress * Math.PI) * JUMP_PEAK_H;
    } else {
      p.jumpT = 0;
      p.jumpHeight = 0;
    }

    // Integrate position
    p.x += p.vx * dt;
    p.z += p.vz * dt;

    // Outer wall collisions
    const minX = -TABLE_W + BALL_R;
    const maxX = TABLE_W - BALL_R;
    const minZ = -TABLE_L + BALL_R;
    const maxZ = TABLE_L - BALL_R;

    if (p.x < minX) {
      p.x = minX;
      p.vx = -p.vx * BOUNCE_RESTITUTION;
      sfx.bounce(0.3);
    } else if (p.x > maxX) {
      p.x = maxX;
      p.vx = -p.vx * BOUNCE_RESTITUTION;
      sfx.bounce(0.3);
    }

    if (p.z < minZ) {
      p.z = minZ;
      p.vz = -p.vz * BOUNCE_RESTITUTION;
      sfx.bounce(0.3);
    } else if (p.z > maxZ) {
      p.z = maxZ;
      p.vz = -p.vz * BOUNCE_RESTITUTION;
      sfx.bounce(0.3);
    }

    // Bumper collisions
    for (const b of this.bumperMeshes) {
      const nearestX = clamp(p.x, b.x - b.hw, b.x + b.hw);
      const nearestZ = clamp(p.z, b.z - b.hd, b.z + b.hd);
      const dist = Math.hypot(p.x - nearestX, p.z - nearestZ);
      if (dist < BALL_R && dist > 0.0001) {
        const nx = (p.x - nearestX) / dist;
        const nz = (p.z - nearestZ) / dist;
        p.x = nearestX + nx * BALL_R;
        p.z = nearestZ + nz * BALL_R;
        const dot = p.vx * nx + p.vz * nz;
        if (dot < 0) {
          p.vx -= 1.65 * dot * nx;
          p.vz -= 1.65 * dot * nz;
          sfx.bounce(0.4);
        }
      }
    }

    // Pit Hole Hazard Detection
    // If the ball is low enough (jumpHeight < 0.25), check for pit falls
    if (p.jumpHeight < 0.25) {
      for (const pit of this.pits) {
        const d = Math.hypot(p.x - pit.x, p.z - pit.z);
        if (d < pit.r * 0.85) {
          // Fell into pit!
          p.falling = true;
          p.fallT = 0;
          p.score = Math.max(0, p.score - 1);
          sfx.crash(0.6);
          sfx.point(false);
          this.ctx.net.buzz(p.pid, 220);
          this.ctx.ui.toast("PIT FALL!", p.label + " -1 Pt", 1100);
          this._spawnSparks(p.x, 0.4, p.z, 0xef4444);
          return;
        }
      }
    }

    // Star Collection Detection
    const dStar = Math.hypot(p.x - this.star.x, p.z - this.star.z);
    if (dStar < BALL_R + this.star.r) {
      p.score += 1;
      sfx.point(true);
      this.ctx.net.buzz(p.pid, 45);
      this.ctx.ui.toast("⭐ STAR COLLECTED!", p.label + " +1 Pt (Total: " + p.score + ")", 1200);
      this._spawnSparks(this.star.x, 0.8, this.star.z, 0xfacc15);
      this._respawnStar();
    }

    // Visual ball updates: rolling rotation + position
    p.group.position.set(p.x, BALL_R + p.jumpHeight, p.z);

    // Roll sphere according to linear displacement
    const rollAngleX = p.vz / BALL_R;
    const rollAngleZ = -p.vx / BALL_R;
    p.sphere.rotation.x += rollAngleX * dt * 1.5;
    p.sphere.rotation.z += rollAngleZ * dt * 1.5;

    // Shadow stays on ground, scales slightly when jumped
    p.shadow.position.set(p.x, 0.02, p.z);
    const shadowScale = clamp(1.0 - p.jumpHeight * 0.35, 0.4, 1.0);
    p.shadow.scale.set(shadowScale, shadowScale, shadowScale);
    p.shadow.visible = true;
  }

  _endGame() {
    let msg = "";
    if (this.players.length === 1) {
      msg = "FINAL SCORE: " + this.players[0].score;
    } else {
      const p1 = this.players[0];
      const p2 = this.players[1];
      if (p1.score > p2.score) {
        msg = "P1 WINS! (" + p1.score + " - " + p2.score + ")";
      } else if (p2.score > p1.score) {
        msg = "P2 WINS! (" + p2.score + " - " + p1.score + ")";
      } else {
        msg = "TIE GAME! (" + p1.score + " - " + p2.score + ")";
      }
    }
    this.ctx.ui.toast("ROUND OVER", msg, 4000);
    sfx.cheer(0.8);
  }

  _updateHud() {
    const sec = Math.ceil(this.timeLeft);
    let html = `
      <div style="display:flex; justify-content:center; align-items:center; gap:24px; pointer-events:none;">
        <div style="background:rgba(15,23,42,0.75); border:2px solid #38bdf8; border-radius:14px; padding:6px 18px; display:flex; align-items:center; gap:10px;">
          <span style="font-size:13px; font-weight:800; color:#38bdf8; letter-spacing:1px;">P1 SCORE</span>
          <span style="font-size:26px; font-weight:900; color:#f8fafc;">${this.players[0] ? this.players[0].score : 0}</span>
        </div>
    `;

    if (this.players[1]) {
      html += `
        <div style="background:rgba(15,23,42,0.75); border:2px solid #f97316; border-radius:14px; padding:6px 18px; display:flex; align-items:center; gap:10px;">
          <span style="font-size:13px; font-weight:800; color:#f97316; letter-spacing:1px;">P2 SCORE</span>
          <span style="font-size:26px; font-weight:900; color:#f8fafc;">${this.players[1].score}</span>
        </div>
      `;
    }

    html += `
        <div style="background:rgba(15,23,42,0.75); border:1px solid rgba(255,255,255,0.2); border-radius:14px; padding:6px 16px; font-size:18px; font-weight:800; color:#fbbf24;">
          ⏱️ ${sec}s
        </div>
      </div>
    `;
    this.ctx.ui.hud(html);
  }
}
