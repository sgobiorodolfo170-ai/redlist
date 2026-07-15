/*!
 * HeartBeat3D.js — 3D 心跳动画组件（Electron / 浏览器通用）
 * 唯一依赖：three（Three.js 核心库，无需任何插件/后处理包）
 *
 * 引入方式：
 *   1) <script src="three.min.js"></script> + <script src="heartbeat3d.js"></script>
 *   2) CommonJS（Electron renderer / 打包器）: const HeartBeat3D = require('./heartbeat3d.js');
 *      （会自动 require('three')）
 *
 * 用法：
 *   const heart = new HeartBeat3D('#container', { bpm: 72, range: [40, 180] });
 *   heart.setBPM(120);
 *
 * License: MIT
 */
(function (global, factory) {
  if (typeof module === 'object' && typeof module.exports === 'object') {
    module.exports = factory(require('three'));           // Electron / CommonJS
  } else if (typeof define === 'function' && define.amd) {
    define(['three'], factory);                           // AMD
  } else {
    global.HeartBeat3D = factory(global.THREE);           // <script> 全局引入
  }
})(typeof window !== 'undefined' ? window : this, function (THREE) {
  'use strict';

  if (!THREE) throw new Error('HeartBeat3D: 未找到 three（Three.js），请先引入依赖');

  var DEFAULTS = {
    bpm: 72,                 // 初始心率
    range: [40, 180],        // 允许的心率范围，setBPM 超出自动钳制
    color: 0xe63946,         // 心脏主色
    emissive: 0xff2740,      // 心跳发光色
    intensity: 1,            // 跳动幅度系数 0.3~2
    rotationSpeed: 0.35,     // 自转速度（弧度/秒），0 为不旋转
    particles: 220,          // 氛围粒子数量，0 关闭
    background: true,        // 自动为容器铺深色渐变氛围背景
    autoStart: true,
    respectReducedMotion: true,
    onBeat: null,            // 每次心跳回调 (bpm) => {}
    onChange: null           // BPM 修改回调 (bpm, clamped) => {}
  };

  function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)); }

  // "扑-通"双相心音波形，p ∈ [0,1) → 0~1
  function waveform(p) {
    var lub = Math.exp(-Math.pow(p - 0.07, 2) / (2 * 0.0009));
    var dub = Math.exp(-Math.pow(p - 0.33, 2) / (2 * 0.0022));
    return lub + 0.55 * dub;
  }

  // 经典心形贝塞尔轮廓 → 挤出为带圆角的 3D 实体
  function buildHeartGeometry() {
    var s = new THREE.Shape();
    s.moveTo(5, 5);
    s.bezierCurveTo(5, 5, 4, 0, 0, 0);
    s.bezierCurveTo(-6, 0, -6, 7, -6, 7);
    s.bezierCurveTo(-6, 11, -3, 15.4, 5, 19);
    s.bezierCurveTo(12, 15.4, 16, 11, 16, 7);
    s.bezierCurveTo(16, 7, 16, 0, 10, 0);
    s.bezierCurveTo(7, 0, 5, 5, 5, 5);

    var geo = new THREE.ExtrudeGeometry(s, {
      depth: 5,
      curveSegments: 32,
      bevelEnabled: true,
      bevelThickness: 3,
      bevelSize: 2.6,
      bevelSegments: 10
    });
    geo.center();
    return geo;
  }

  // 生成径向光晕贴图（用 Canvas 画，避免引入后处理 Bloom 依赖）
  function makeGlowTexture(rgb) {
    var c = document.createElement('canvas');
    c.width = c.height = 128;
    var ctx = c.getContext('2d');
    var g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
    g.addColorStop(0, 'rgba(' + rgb + ',0.55)');
    g.addColorStop(0.4, 'rgba(' + rgb + ',0.18)');
    g.addColorStop(1, 'rgba(' + rgb + ',0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 128, 128);
    var tex = new THREE.Texture(c);
    tex.needsUpdate = true;
    return tex;
  }

  // 生成心形粒子贴图
  function makeHeartTexture() {
    var c = document.createElement('canvas');
    c.width = c.height = 64;
    var ctx = c.getContext('2d');
    ctx.beginPath();
    ctx.moveTo(32, 52);
    ctx.bezierCurveTo(32, 52, 14, 42, 10, 30);
    ctx.bezierCurveTo(6, 20, 12, 8, 22, 10);
    ctx.bezierCurveTo(28, 11, 32, 18, 32, 22);
    ctx.bezierCurveTo(32, 18, 36, 11, 42, 10);
    ctx.bezierCurveTo(52, 8, 58, 20, 54, 30);
    ctx.bezierCurveTo(50, 42, 32, 52, 32, 52);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    var tex = new THREE.Texture(c);
    tex.needsUpdate = true;
    return tex;
  }

  function HeartBeat3D(target, options) {
    if (!(this instanceof HeartBeat3D)) return new HeartBeat3D(target, options);

    this.el = typeof target === 'string' ? document.querySelector(target) : target;
    if (!this.el) throw new Error('HeartBeat3D: 找不到容器元素 ' + target);

    this.opts = {};
    for (var k in DEFAULTS) {
      this.opts[k] = options && options[k] !== undefined ? options[k] : DEFAULTS[k];
    }

    this._phase = 0;
    this._lastT = null;
    this._elapsed = 0;
    this._raf = null;
    this._running = false;
    this._bpm = clamp(this.opts.bpm, this.opts.range[0], this.opts.range[1]);
    this._reduced = this.opts.respectReducedMotion &&
      typeof matchMedia === 'function' &&
      matchMedia('(prefers-reduced-motion: reduce)').matches;

    this._initScene();
    this._renderOnce();
    if (this.opts.autoStart) this.start();
  }

  HeartBeat3D.prototype._initScene = function () {
    var o = this.opts;
    var w = this.el.clientWidth || 400;
    var h = this.el.clientHeight || 400;

    // 氛围背景：深红-紫-墨的星云渐变 + 暗角
    if (o.background) {
      this.el.style.background = '#ffffff';
    }
    if (getComputedStyle(this.el).position === 'static') {
      this.el.style.position = 'relative';
    }

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.setSize(w, h);
    this.renderer.domElement.style.display = 'block';
    this.el.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xffffff);
    this.scene.fog = new THREE.Fog(0xffffff, 45, 95);

    this.camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 200);
    this.camera.position.set(0, 0, 46);

    // 灯光：环境 + 主光 + 冷色轮廓光，塑造立体感
    this.scene.add(new THREE.AmbientLight(0x606080, 0.5));
    this._keyLight = new THREE.PointLight(0xff5566, 1.4, 140);
    this._keyLight.position.set(18, 20, 30);
    this.scene.add(this._keyLight);
    var rim = new THREE.DirectionalLight(0x4455aa, 1.0); // 冷色逆光勾边
    rim.position.set(-20, -8, -18);
    this.scene.add(rim);
    var fill = new THREE.DirectionalLight(0x88ccff, 0.35); // 底部补光
    fill.position.set(0, -20, 10);
    this.scene.add(fill);

    // 3D 心脏
    this._heartGroup = new THREE.Group();
    this._material = new THREE.MeshStandardMaterial({
      color: o.color,
      emissive: o.emissive,
      emissiveIntensity: 0.25,
      roughness: 0.25,
      metalness: 0.20
    });
    var mesh = new THREE.Mesh(buildHeartGeometry(), this._material);
    mesh.rotation.z = Math.PI;      // 心形轮廓默认尖朝上，翻转朝下
    mesh.scale.setScalar(0.95);
    this._heartGroup.add(mesh);
    this._mesh = mesh;

    // 心脏背后的光晕（Canvas 贴图 Sprite，替代 Bloom 后处理，省一个依赖）
    this._glow = new THREE.Sprite(new THREE.SpriteMaterial({
      map: makeGlowTexture('255,60,80'),
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      transparent: true
    }));
    this._glow.scale.set(46, 46, 1);
    this._glow.position.z = -6;
    this.scene.add(this._glow);
    this.scene.add(this._heartGroup);

    // 氛围粒子：缓慢上浮的微光尘埃
    if (o.particles > 0) this._initParticles(o.particles);
    if (o.particles > 0) this._initSparkles(80);
    this._initTrail();

    // 自适应容器尺寸
    var self = this;
    this._onResize = function () {
      var w2 = self.el.clientWidth, h2 = self.el.clientHeight;
      if (!w2 || !h2) return;
      self.camera.aspect = w2 / h2;
      self.camera.updateProjectionMatrix();
      self.renderer.setSize(w2, h2);
      if (!self._running) self._renderOnce();
    };
    if (typeof ResizeObserver === 'function') {
      this._ro = new ResizeObserver(this._onResize);
      this._ro.observe(this.el);
    } else {
      window.addEventListener('resize', this._onResize);
    }
  };

  HeartBeat3D.prototype._initParticles = function (count) {
    var pos = new Float32Array(count * 3);
    this._pVel = new Float32Array(count);
    for (var i = 0; i < count; i++) {
      pos[i * 3]     = (Math.random() - 0.5) * 70;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 44;
      pos[i * 3 + 2] = -28 + Math.random() * 36;
      this._pVel[i]  = 0.6 + Math.random() * 1.4;
    }
    var geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    this._particles = new THREE.Points(geo, new THREE.PointsMaterial({
      color: 0xff69b4,
      size: 4.5,
      map: makeHeartTexture(),
      transparent: true,
      opacity: 1.0,
      blending: THREE.NormalBlending,
      depthWrite: true,
      sizeAttenuation: true
    }));
    this.scene.add(this._particles);
  };

  HeartBeat3D.prototype._initSparkles = function (count) {
    var pos = new Float32Array(count * 3);
    var col = new Float32Array(count * 3);
    this._sPhase = new Float32Array(count);
    this._sSpeed = new Float32Array(count);
    for (var i = 0; i < count; i++) {
      pos[i * 3]     = (Math.random() - 0.5) * 80;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 50;
      pos[i * 3 + 2] = -30 + Math.random() * 40;
      this._sPhase[i] = Math.random() * Math.PI * 2;
      this._sSpeed[i] = 2 + Math.random() * 4;
      col[i * 3] = col[i * 3 + 1] = col[i * 3 + 2] = 1;
    }
    var geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
    var c = document.createElement('canvas');
    c.width = c.height = 32;
    var ctx = c.getContext('2d');
    var cx = 16, cy = 16, spikes = 4, outerR = 14, innerR = 4;
    ctx.beginPath();
    for (var i = 0; i < spikes * 2; i++) {
      var r = (i % 2 === 0) ? outerR : innerR;
      var angle = (i * Math.PI / spikes) - Math.PI / 2;
      var x = cx + r * Math.cos(angle);
      var y = cy + r * Math.sin(angle);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.closePath();
    var grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, outerR);
    grad.addColorStop(0, 'rgba(255,255,255,1)');
    grad.addColorStop(0.4, 'rgba(255,230,240,1)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = grad;
    ctx.fill();
    var tex = new THREE.Texture(c);
    tex.needsUpdate = true;
    this._sparkles = new THREE.Points(geo, new THREE.PointsMaterial({
      size: 1.5,
      map: tex,
      transparent: true,
      opacity: 1.0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      vertexColors: true,
      sizeAttenuation: true
    }));
    this.scene.add(this._sparkles);
  };

  HeartBeat3D.prototype._initTrail = function () {
    this._trailMax = 80;
    this._trailData = [];
    this._trailLastX = null;
    this._trailLastY = null;
    var pos = new Float32Array(this._trailMax * 3);
    var col = new Float32Array(this._trailMax * 3);
    var geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
    geo.setDrawRange(0, 0);
    this._trail = new THREE.Points(geo, new THREE.PointsMaterial({
      size: 3.0,
      map: makeHeartTexture(),
      transparent: true,
      opacity: 0.7,
      blending: THREE.NormalBlending,
      depthWrite: false,
      vertexColors: true,
      sizeAttenuation: true
    }));
    this.scene.add(this._trail);
    var self = this;
    this._onMouseMove = function (event) {
      if (!self._running) return;
      var rect = self.renderer.domElement.getBoundingClientRect();
      var mx = event.clientX - rect.left;
      var my = event.clientY - rect.top;
      if (self._trailLastX !== null) {
        var dx = mx - self._trailLastX, dy = my - self._trailLastY;
        if (dx * dx + dy * dy < 25) return;
      }
      self._trailLastX = mx;
      self._trailLastY = my;
      var x = (mx / rect.width) * 2 - 1;
      var y = -(my / rect.height) * 2 + 1;
      var vec = new THREE.Vector3(x, y, 0.5).unproject(self.camera);
      var dir = vec.sub(self.camera.position).normalize();
      var dist = -self.camera.position.z / dir.z;
      var p = self.camera.position.clone().add(dir.multiplyScalar(dist));
      self._trailData.push({ x: p.x, y: p.y, z: p.z, age: 0 });
      if (self._trailData.length > self._trailMax) self._trailData.shift();
    };
    this._onMouseLeave = function () {
      self._trailLastX = null;
      self._trailLastY = null;
    };
    var canvas = this.renderer.domElement;
    canvas.addEventListener('mousemove', this._onMouseMove);
    canvas.addEventListener('mouseleave', this._onMouseLeave);
  };

  HeartBeat3D.prototype._update = function (dt) {
    var prevPhase = this._phase;
    this._phase += dt * this._bpm / 60;
    if (this._phase >= 1) {
      this._phase %= 1;
      if (typeof this.opts.onBeat === 'function') this.opts.onBeat(this._bpm);
    }
    this._elapsed += dt;

    var amp = this._reduced ? 0.03 : 0.11 * this.opts.intensity;
    var w = waveform(this._phase);

    // 收缩 + 发光 + 光晕同步脉动
    this._heartGroup.scale.setScalar(1 + amp * w);
    this._material.emissiveIntensity = 0.22 + 0.95 * w;
    this._keyLight.intensity = 1.3 + 1.1 * w;
    this._glow.material.opacity = 0.5 + 0.5 * w;
    this._glow.scale.setScalar(46 * (1 + 0.12 * w));

    // 缓慢自转 + 相机轻微呼吸浮动
    if (!this._reduced) {
      this._heartGroup.rotation.y += this.opts.rotationSpeed * dt;
      this.camera.position.y = Math.sin(this._elapsed * 0.5) * 0.9;
      this.camera.lookAt(0, 0, 0);
    }

    // 粒子上浮，越界回卷
    if (this._particles) {
      var arr = this._particles.geometry.attributes.position.array;
      for (var i = 0; i < this._pVel.length; i++) {
        arr[i * 3 + 1] += this._pVel[i] * dt;
        if (arr[i * 3 + 1] > 24) arr[i * 3 + 1] = -24;
      }
      this._particles.geometry.attributes.position.needsUpdate = true;
      this._particles.material.opacity = 0.4 + 0.3 * w;
      this._particles.material.size = 4.5 + 0.8 * Math.sin(this._elapsed * 6);
    }
    if (this._sparkles) {
      var sc = this._sparkles.geometry.attributes.color.array;
      var scLen = this._sparkles.geometry.attributes.position.count;
      for (var i = 0; i < scLen; i++) {
        var b = 0.3 + 0.7 * (0.5 + 0.5 * Math.sin(this._elapsed * this._sSpeed[i] + this._sPhase[i]));
        sc[i * 3] = sc[i * 3 + 1] = sc[i * 3 + 2] = b;
      }
      this._sparkles.geometry.attributes.color.needsUpdate = true;
    }
    if (this._trail) {
      var td = this._trailData;
      var tp = this._trail.geometry.attributes.position.array;
      var tc = this._trail.geometry.attributes.color.array;
      var alive = 0;
      for (var i = 0; i < td.length; i++) {
        td[i].age += dt;
        if (td[i].age > 0.5) continue;
        tp[alive * 3] = td[i].x;
        tp[alive * 3 + 1] = td[i].y;
        tp[alive * 3 + 2] = td[i].z;
        var t = td[i].age / 0.5;
        tc[alive * 3]     = 1.0 - t * 0.2;
        tc[alive * 3 + 1] = 0.41 - t * 0.08;
        tc[alive * 3 + 2] = 0.71 - t * 0.38;
        alive++;
      }
      this._trail.geometry.setDrawRange(0, alive);
      this._trail.geometry.attributes.position.needsUpdate = true;
      this._trail.geometry.attributes.color.needsUpdate = true;
    }
  };

  HeartBeat3D.prototype._tick = function (t) {
    if (!this._running) return;
    if (this._lastT === null) this._lastT = t;
    var dt = Math.min((t - this._lastT) / 1000, 0.05); // 防切后台大步长
    this._lastT = t;
    this._update(dt);
    this.renderer.render(this.scene, this.camera);
    var self = this;
    this._raf = requestAnimationFrame(function (tt) { self._tick(tt); });
  };

  HeartBeat3D.prototype._renderOnce = function () {
    this.renderer.render(this.scene, this.camera);
  };

  /* ---------------- 公共接口（与 2D 版 HeartBeat 完全一致） ---------------- */

  HeartBeat3D.prototype.setBPM = function (bpm) {
    var v = clamp(Number(bpm) || 0, this.opts.range[0], this.opts.range[1]);
    var clamped = v !== Number(bpm);
    this._bpm = v;
    if (typeof this.opts.onChange === 'function') this.opts.onChange(v, clamped);
    return v;
  };

  HeartBeat3D.prototype.getBPM = function () { return this._bpm; };

  HeartBeat3D.prototype.setRange = function (min, max) {
    if (min >= max) throw new Error('HeartBeat3D: range 需满足 min < max');
    this.opts.range = [min, max];
    this.setBPM(this._bpm);
  };

  HeartBeat3D.prototype.getRange = function () { return this.opts.range.slice(); };

  HeartBeat3D.prototype.start = function () {
    if (this._running) return;
    this._running = true;
    this._lastT = null;
    var self = this;
    this._raf = requestAnimationFrame(function (t) { self._tick(t); });
  };

  HeartBeat3D.prototype.stop = function () {
    this._running = false;
    if (this._raf) cancelAnimationFrame(this._raf);
    this._heartGroup.scale.setScalar(1);
    this._material.emissiveIntensity = 0.25;
    this._renderOnce();
  };

  HeartBeat3D.prototype.isRunning = function () { return this._running; };

  HeartBeat3D.prototype.setIntensity = function (v) {
    this.opts.intensity = clamp(Number(v) || 1, 0.1, 3);
  };

  HeartBeat3D.prototype.destroy = function () {
    this.stop();
    if (this._ro) this._ro.disconnect();
    else window.removeEventListener('resize', this._onResize);
    this._mesh.geometry.dispose();
    this._material.dispose();
    this._glow.material.map.dispose();
    this._glow.material.dispose();
    if (this._particles) {
      this._particles.geometry.dispose();
      this._particles.material.dispose();
    }
    if (this._sparkles) {
      this._sparkles.geometry.dispose();
      this._sparkles.material.dispose();
    }
    if (this._trail) {
      if (this._onMouseMove) {
        var canvas = this.renderer && this.renderer.domElement;
        if (canvas) {
          canvas.removeEventListener('mousemove', this._onMouseMove);
          canvas.removeEventListener('mouseleave', this._onMouseLeave);
        }
      }
      this._trail.geometry.dispose();
      this._trail.material.dispose();
    }
    this.renderer.dispose();
    if (this.renderer.domElement.parentNode === this.el) {
      this.el.removeChild(this.renderer.domElement);
    }
  };

  return HeartBeat3D;
});
