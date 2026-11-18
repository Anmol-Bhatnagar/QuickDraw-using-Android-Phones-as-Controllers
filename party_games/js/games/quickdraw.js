/**
 * Quickdraw Game Bridge in the 3D Console Arena.
 * Coordinates between the browser screen, the phone controller,
 * and the Python camera/voice game engine.
 */

import * as THREE from "../../lib/three.module.js";
import { skyDome, addLights } from "../arena.js";

export class QuickdrawGame {
  constructor(ctx) {
    this.ctx = ctx;
    this.name = "Quickdraw";
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(50, 16 / 9, 0.1, 100);
    this.camera.position.set(0, 1.5, 4);

    this.scene.add(skyDome(0x2b1d0c, 0xd4883b));
    addLights(this.scene);
  }

  enter() {
    // Notify controller of Quickdraw mode
    this.ctx.net.mode(0, "Quickdraw Duel",
      "Holster phone. Listen to the outlaw. Shoot on target word!",
      "FIRE", "Tap or press Volume Up/Down");
    this.ctx.net.send({ t: "mode", layout: "quickdraw" });

    // Launch the Python camera & voice engine
    this.ctx.net.send({ t: "launch_python_game", id: "quickdraw" });

    this.ctx.ui.hud(`
      <div class="hudRow">
        <span class="tag" style="background:#ff9900;color:#000;font-weight:900;">WILD WEST DUEL</span>
      </div>
      <div class="hudSub">Look at the laptop camera window! Holster your phone & listen carefully.</div>
    `);
    this.ctx.ui.prompt("Press ESC or Phone HOME to return to Game Library");
  }

  exit() {
    this.ctx.net.send({ t: "stop_python_game", id: "quickdraw" });
    this.ctx.ui.prompt("");
    this.ctx.ui.hud("");
  }

  update(dt, now) {
    // Keep 3D scene alive in background
  }

  onButton(down, pid, key) {
    if (down) {
      this.ctx.net.send({
        t: "shoot",
        player: "player" + pid,
        time: Date.now()
      });
    }
  }
}
