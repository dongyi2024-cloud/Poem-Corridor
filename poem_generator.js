/**
 * Poem Loop Generator - 秩序与情绪转换版 (波动连贯优化)
 * 核心修复：将自转由“独立随机速度”改为“全局相位映射”
 */

import * as THREE from 'three';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';

// ==================== 全局变量 ====================
let scene, camera, renderer, clock;
let poemLoopGroup = null;
let isEntering = false;
let isLooping = false;
let loopTheta = 0;
let poemLines = [];
let currentPoemIndex = -1;
let isMoving = false;
let isPaused = false;

// ==================== CONFIG ====================
export const CONFIG = {
    loop: {
        radius: 10.0,       // 稍微增大半径，确保中心空洞感
        height: 1.5,
        stepAngle: 0.1,
        moveDuration: 1.2,
        moveEase: 'power2.inOut',
        lookAheadOffset: 0.15
    },
    fog: { color: 0x0a0a0f, overviewDensity: 0.02, loopDensity: 0.12 },
    camera: { fov: 60, near: 0.1, far: 1000 },
    overview: { altitude: 20, distance: 28, duration: 45, floatAmp: 1.5 },
    transition: { duration: 3.5, ease: 'power2.inOut' },
    numPoints: 160,
    frameThickness: 0.05,
    framePoleThickness: 0.06,
    zAmplitude: 1.2
};

// ==================== 情感分析逻辑 ====================
const positiveWords = new Set(['love', 'lovely', 'beautiful', 'bright', 'warm', 'happy', 'joy', 'hope', 'dream', 'light', 'shine', 'glow', 'golden', 'sweet', 'gentle', 'kind', 'soft', 'tender', 'fair', 'long', 'eternal', 'summer']);
const negativeWords = new Set(['dark', 'cold', 'sad', 'fear', 'fade', 'death', 'lose', 'lost', 'brief', 'short', 'dimm', 'dull', 'rough', 'harsh', 'hate', 'wrong', 'weak', 'fate', 'night']);

function simpleAnalyze(text) {
    const words = text.toLowerCase().split(/\W+/);
    let score = 0, matched = 0;
    words.forEach(word => {
        if (positiveWords.has(word)) { score += 0.5; matched++; }
        if (negativeWords.has(word)) { score -= 0.5; matched++; }
    });
    return {
        polarity: Math.max(-1, Math.min(1, score)),
        subjectivity: Math.min(1, (matched / (words.length || 1)) * 3)
    };
}

// ==================== 算法核心函数 ====================

function cosineInterpolate(y1, y2, mu) {
    const mu2 = (1 - Math.cos(mu * Math.PI)) / 2;
    return y1 * (1 - mu2) + y2 * mu2;
}

function remapNonlinear(value, out_min, out_max, exponent = 1.5) {
    const sign = value >= 0 ? 1 : -1;
    const amplified = sign * Math.pow(Math.abs(value), exponent);
    return out_min + (amplified + 1) / 2 * (out_max - out_min);
}

function createToriiFrame(w, h, depth, t) {
    const group = new THREE.Group();
    const material = new THREE.MeshStandardMaterial({
        color: 0xffffff, 
        emissive: 0xffffff, 
        emissiveIntensity: 0.2,
        roughness: 0.4, 
        metalness: 0.2, 
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.9
    });

    const boxes = [
        { s: [w + 2 * t, t, depth], p: [0, h / 2 + t / 2, 0] },
        { s: [w + 2 * t, t, depth], p: [0, -(h / 2 + t / 2), 0] },
        { s: [t, h, depth], p: [-(w / 2 + t / 2), 0, 0] },
        { s: [t, h, depth], p: [(w / 2 + t / 2), 0, 0] }
    ];

    boxes.forEach(box => {
        const mesh = new THREE.Mesh(new THREE.BoxGeometry(...box.s), material);
        mesh.position.set(...box.p);
        group.add(mesh);
    });
    return group;
}

/**
 * 核心生形引擎
 */
function buildPoemLoop(originalData, isDefault = false) {
    const NUM_POINTS = CONFIG.numPoints;
    const R = CONFIG.loop.radius;
    const n = originalData.length;
    const container = new THREE.Group();

    // 1. 数据平滑插值
    const smoothData = [];
    for (let i = 0; i < NUM_POINTS; i++) {
        const tt = i / NUM_POINTS;
        const idxRaw = tt * n;
        const i1 = Math.floor(idxRaw) % n;
        const i2 = (i1 + 1) % n;
        const f = idxRaw - Math.floor(idxRaw);

        smoothData.push({
            pol: isDefault ? 0 : cosineInterpolate(originalData[i1].polarity, originalData[i2].polarity, f),
            sub: isDefault ? 0 : cosineInterpolate(originalData[i1].subjectivity, originalData[i2].subjectivity, f)
        });
    }

    // 2. 拓扑装配
    for (let i = 0; i < NUM_POINTS; i++) {
        const data = smoothData[i];
        const theta = (i / NUM_POINTS) * Math.PI * 2;

        // 限制宽高范围，防止挤占圆心
        const w = isDefault ? 3.0 : remapNonlinear(data.pol, 2.5, 5.0, 1.2);
        const h = isDefault ? 3.0 : remapNonlinear(data.pol, 2.8, 6.0, 1.2);

        const frame = createToriiFrame(w, h, CONFIG.frameThickness, CONFIG.framePoleThickness);

        // 位置计算
        const posX = R * Math.cos(theta);
        const posZ = R * Math.sin(theta);
        const posY = isDefault ? 0 : Math.sin(theta * 2) * CONFIG.zAmplitude * data.sub;

        frame.position.set(posX, posY, posZ);
        frame.rotation.y = -theta;

        // 将情感数据存入 userData，供 animate 函数实时计算旋转角度
        frame.userData = {
            index: i,
            polarity: data.pol,
            subjectivity: data.sub,
            isDefault: isDefault
        };

        container.add(frame);
    }

    container.name = 'PoemLoopGroup';
    return container;
}

// ==================== 接口逻辑 ====================

export function rebuildModel(text) {
    if (poemLoopGroup) scene.remove(poemLoopGroup);
    poemLines = [];

    const lines = text.split('\n').filter(l => l.trim());
    const rawData = lines.map(line => {
        poemLines.push(line.trim());
        return simpleAnalyze(line);
    });

    if (rawData.length === 0) {
        poemLoopGroup = buildPoemLoop([], true);
    } else {
        if (rawData.length === 1) rawData.push({...rawData[0]});
        poemLoopGroup = buildPoemLoop(rawData, false);
    }
    scene.add(poemLoopGroup);
}

export function exportToGLB(group, filename = 'emotion_loop.glb') {
    const exporter = new GLTFExporter();
    exporter.parse(group, (gltf) => {
        const blob = new Blob([gltf], { type: 'application/octet-stream' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.click();
        URL.revokeObjectURL(url);
    }, (error) => { console.error('导出失败:', error); }, { binary: true });
}

export function initThreeJS(containerId = 'canvas-container') {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(CONFIG.fog.color);
    scene.fog = new THREE.FogExp2(CONFIG.fog.color, CONFIG.fog.overviewDensity);
    camera = new THREE.PerspectiveCamera(CONFIG.camera.fov, window.innerWidth / window.innerHeight, 0.1, 1000);
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    document.getElementById(containerId).appendChild(renderer.domElement);
    clock = new THREE.Clock();

    scene.add(new THREE.AmbientLight(0xffffff, 0.4));
    const pl = new THREE.PointLight(0xffeedd, 2.0, 60);
    pl.position.set(0, 10, 0);
    scene.add(pl);

    return { scene, camera, renderer, clock };
}

export function init(containerId, onReady) {
    const result = initThreeJS(containerId);
    poemLoopGroup = buildPoemLoop([], true);
    scene.add(poemLoopGroup);
    if (onReady) onReady(result);
    return result;
}

export function animate() {
    const fn = () => {
        requestAnimationFrame(fn);
        const time = clock.getElapsedTime();

        if (poemLoopGroup && !isPaused) {
            poemLoopGroup.children.forEach((frame, i) => {
                const { polarity, subjectivity, isDefault } = frame.userData;
                
                if (isDefault) {
                    // 初始状态：轻微整齐的呼吸
                    frame.rotation.z = Math.sin(time * 0.5 - i * 0.05) * 0.1;
                } else {
                    // 情感驱动逻辑：绝对角度映射
                    // 1. 基础扭转：极性决定方向 (Polarity -> Twist)
                    const baseTwist = polarity * Math.PI * 0.8; 
                    
                    // 2. 动态波动：主观性决定振幅 (Subjectivity -> Wave Amplitude)
                    // time * 1.2 决定速度，i * 0.15 决定相位差（产生连贯波动感）
                    const wave = Math.sin(time * 1.2 - i * 0.15) * (subjectivity * 0.6 + 0.1);
                    
                    // 应用最终旋转（不再是累加，而是直接赋值确保有序）
                    frame.rotation.z = baseTwist + wave;
                }
            });
        }

        if (isLooping) {
            const R = CONFIG.loop.radius;
            camera.position.set(R * Math.cos(loopTheta), CONFIG.loop.height, R * Math.sin(loopTheta));
            camera.lookAt(R * Math.cos(loopTheta + 0.1), CONFIG.loop.height, R * Math.sin(loopTheta + 0.1));
        } else {
            const angle = time * 0.1;
            camera.position.set(Math.cos(angle) * CONFIG.overview.distance, CONFIG.overview.altitude, Math.sin(angle) * CONFIG.overview.distance);
            camera.lookAt(0, 0, 0);
        }

        renderer.render(scene, camera);
    };
    fn();
}

// ==================== 状态控制接口 ====================
export function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

export function getConfig() { return CONFIG; }
export function getCamera() { return camera; }
export function getScene() { return scene; }
export function setLooping(v) { isLooping = v; }
export function setLoopTheta(v) { loopTheta = v; }
export function getLoopTheta() { return loopTheta; }
export function setPaused(v) { isPaused = v; }
export function getPoemLines() { return poemLines; }
export function getIsLooping() { return isLooping; }
export function getEntering() { return isEntering; }
export function setEntering(v) { isEntering = v; }
export function getIsMoving() { return isMoving; }
export function setIsMoving(v) { isMoving = v; }
export function getCurrentPoemIndex() { return currentPoemIndex; }
export function setCurrentPoemIndex(v) { currentPoemIndex = v; }
export function getPaused() { return isPaused; }
export function setFogDensity(density) { scene.fog = new THREE.FogExp2(CONFIG.fog.color, density); }
