"use client";

import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { Shield, FileCode2, GitFork, Zap, RotateCcw } from "lucide-react";

export const PILLARS_DATA = [
  {
    id: "secure_ai",
    number: "1",
    title: "Secure AI",
    subtitle: "Air-gapped database isolation with automatic civilian PII masking",
    icon: Shield,
    desc: "Confidential police FIR records remain completely isolated from public networks. Inquiries pass through an air-lock gateway that automatically masks civilian Aadhaar and phone numbers before any model can process the case.",
  },
  {
    id: "agents_identity",
    number: "2",
    title: "Agents.md & Identity",
    subtitle: "Executable architecture contract that compiles agent roles and routes with zero drift",
    icon: FileCode2,
    desc: "Our orchestrator fleet and routing table compile directly from AGENTS.md at startup. If the codebase and documentation disagree by a single route or permission, the build fails immediately—preventing ghost agents and silent fallbacks.",
  },
  {
    id: "agent_routing",
    number: "3",
    title: "Agent Routing & Searching",
    subtitle: "Parallel dispatch across verified database templates, network graphs, and vector memory",
    icon: GitFork,
    desc: "Instead of relying on a single slow model, an intent supervisor routes questions simultaneously across fixed FIR templates, criminal network graphs, and semantic memory—returning verified facts in seconds without hallucinated connections.",
  },
  {
    id: "system1_approach",
    number: "4",
    title: "System 1 Approach",
    subtitle: "Fast deterministic code execution, reserving language models only for multi-source synthesis",
    icon: Zap,
    desc: "We use direct code execution for factual database lookups, delivering answers in 38 milliseconds without hallucination risk. Generative models are invoked only when synthesizing findings from multiple specialist agents, strictly bound by citation verification.",
  }
];

function SinglePillarCanvas({ pillarIndex }) {
  const containerRef = useRef(null);
  const isDragging = useRef(false);
  const mousePos = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const width = container.clientWidth || 390;
    const height = 200;

    // Scene & Camera - Isometric Architectural Perspective
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xFAFAFB);

    const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
    camera.position.set(4.0, 3.2, 4.6);
    camera.lookAt(0, 0, 0);

    // Renderer
    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      container.innerHTML = "";
      container.appendChild(renderer.domElement);
    } catch (e) {
      console.warn("WebGL initialization skipped:", e);
      return;
    }

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xFFFFFF, 1.2);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xFFFFFF, 1.6);
    dirLight1.position.set(6, 10, 6);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x0A7E8C, 0.8);
    dirLight2.position.set(-6, -4, -4);
    scene.add(dirLight2);

    // Subtle Ground Grid
    const grid = new THREE.GridHelper(5.5, 12, 0xCBD5E1, 0xEEF2F6);
    grid.position.y = -1.2;
    scene.add(grid);

    // Scene group for rotation
    const group = new THREE.Group();
    scene.add(group);

    let animUpdate = () => {};

    // ─────────────────────────────────────────────────────────────
    // SCENE 0: SECURE AI & AIR-GAPPED POLICE VAULT
    // ─────────────────────────────────────────────────────────────
    if (pillarIndex === 0) {
      const platGeo = new THREE.BoxGeometry(4.2, 0.15, 2.8);
      const platMat = new THREE.MeshStandardMaterial({ color: 0xF1F5F9, roughness: 0.9 });
      const plat = new THREE.Mesh(platGeo, platMat);
      plat.position.y = -1.2;
      group.add(plat);

      // DMZ Platform on Left
      const dmzGeo = new THREE.BoxGeometry(1.4, 0.2, 2.0);
      const dmzMat = new THREE.MeshStandardMaterial({ color: 0xE2E8F0 });
      const dmz = new THREE.Mesh(dmzGeo, dmzMat);
      dmz.position.set(-1.4, -1.0, 0);
      group.add(dmz);

      // DMZ OSINT Terminal Node
      const osintNodeGeo = new THREE.BoxGeometry(0.35, 0.55, 0.35);
      const osintMat = new THREE.MeshStandardMaterial({ color: 0xF59E0B, metalness: 0.5 });
      const osintNode = new THREE.Mesh(osintNodeGeo, osintMat);
      osintNode.position.set(-1.4, -0.65, 0);
      group.add(osintNode);

      // Center: Translucent Holographic Air-Gap Firewall Gate
      const wallGeo = new THREE.BoxGeometry(0.1, 1.7, 2.4);
      const wallMat = new THREE.MeshPhysicalMaterial({
        color: 0x0A7E8C,
        transparent: true,
        opacity: 0.35,
        roughness: 0.1,
        transmission: 0.7
      });
      const wall = new THREE.Mesh(wallGeo, wallMat);
      wall.position.set(-0.35, -0.25, 0);
      group.add(wall);

      // Vertical Laser Scan Bar
      const laserGeo = new THREE.CylinderGeometry(0.025, 0.025, 2.4);
      const laserMat = new THREE.MeshBasicMaterial({ color: 0x22E6F0 });
      const laser = new THREE.Mesh(laserGeo, laserMat);
      laser.rotation.x = Math.PI / 2;
      laser.position.set(-0.33, 0.3, 0);
      group.add(laser);

      // Sovereign Police Data Vault (Server Racks)
      const rackGeo = new THREE.BoxGeometry(0.4, 1.2, 0.6);
      const rackMat = new THREE.MeshStandardMaterial({ color: 0x1E293B, metalness: 0.5, roughness: 0.2 });

      const r1 = new THREE.Mesh(rackGeo, rackMat);
      r1.position.set(0.6, -0.4, -0.5);
      const r2 = new THREE.Mesh(rackGeo, rackMat);
      r2.position.set(1.3, -0.4, -0.5);
      const r3 = new THREE.Mesh(rackGeo, rackMat);
      r3.position.set(0.9, -0.4, 0.4);
      group.add(r1, r2, r3);

      // Core Verified Master Cylinder
      const coreGeo = new THREE.CylinderGeometry(0.3, 0.3, 0.5, 16);
      const coreMat = new THREE.MeshStandardMaterial({ color: 0x0A7E8C, metalness: 0.7 });
      const core = new THREE.Mesh(coreGeo, coreMat);
      core.position.set(0.9, 0.5, 0.4);
      group.add(core);

      // Rejected PII Token (Red)
      const piiGeo = new THREE.BoxGeometry(0.18, 0.18, 0.18);
      const piiMat = new THREE.MeshBasicMaterial({ color: 0xEF4444 });
      const pii = new THREE.Mesh(piiGeo, piiMat);
      pii.position.set(-0.55, 0.1, 0.3);
      group.add(pii);

      // Clean Admitted Token (Emerald)
      const cleanGeo = new THREE.BoxGeometry(0.18, 0.18, 0.18);
      const cleanMat = new THREE.MeshBasicMaterial({ color: 0x10B981 });
      const clean = new THREE.Mesh(cleanGeo, cleanMat);
      clean.position.set(0.2, 0.1, -0.2);
      group.add(clean);

      animUpdate = (t) => {
        laser.position.y = -0.6 + (Math.sin(t * 2.2) + 1) * 0.7;
        core.rotation.y = t * 0.6;
        pii.rotation.x = t;
        clean.rotation.y = t;
        clean.position.x = 0.15 + Math.sin(t * 1.5) * 0.35;
      };

    // ─────────────────────────────────────────────────────────────
    // SCENE 1: AGENTS.MD MANIFEST & IMMUTABLE IDENTITY
    // ─────────────────────────────────────────────────────────────
    } else if (pillarIndex === 1) {
      // Upper Level: AGENTS.md Architectural Blueprint Slate
      const docGeo = new THREE.BoxGeometry(2.3, 0.08, 1.5);
      const docMat = new THREE.MeshStandardMaterial({ color: 0xFFFFFF, roughness: 0.1 });
      const docSlate = new THREE.Mesh(docGeo, docMat);
      docSlate.position.set(0, 1.0, 0);
      group.add(docSlate);

      // Blueprint Header
      const headerGeo = new THREE.BoxGeometry(2.1, 0.04, 0.3);
      const headerMat = new THREE.MeshStandardMaterial({ color: 0x0A7E8C });
      const header = new THREE.Mesh(headerGeo, headerMat);
      header.position.set(0, 1.05, -0.45);
      group.add(header);

      // Center: manifest.py Compiler Core
      const compGeo = new THREE.CylinderGeometry(0.35, 0.35, 0.28, 8);
      const compMat = new THREE.MeshStandardMaterial({ color: 0x10B981, metalness: 0.8 });
      const compCore = new THREE.Mesh(compGeo, compMat);
      compCore.position.set(0, 0.05, 0);
      group.add(compCore);

      // Lower Level: 6 Compiled LangGraph Agent Modules
      const agentRacks = [];
      const count = 6;
      for (let i = 0; i < count; i++) {
        const aGeo = new THREE.BoxGeometry(0.4, 0.45, 0.4);
        const aMat = new THREE.MeshStandardMaterial({ color: 0x1E293B, metalness: 0.5 });
        const aRack = new THREE.Mesh(aGeo, aMat);
        const angle = (i / count) * Math.PI * 2;
        const x = Math.cos(angle) * 1.5;
        const z = Math.sin(angle) * 1.3;
        aRack.position.set(x, -0.85, z);
        group.add(aRack);
        agentRacks.push(aRack);

        // Vertical Laser Conduits linking Doc -> Compiler -> Agents
        const lineGeo = new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(x * 0.6, 0.9, z * 0.6),
          new THREE.Vector3(0, 0.05, 0),
          new THREE.Vector3(x, -0.6, z)
        ]);
        const line = new THREE.Line(lineGeo, new THREE.LineBasicMaterial({ color: 0x0A7E8C, transparent: true, opacity: 0.5 }));
        group.add(line);
      }

      animUpdate = (t) => {
        compCore.rotation.y = t * 1.2;
        docSlate.position.y = 1.0 + Math.sin(t * 1.5) * 0.05;
        header.position.y = 1.05 + Math.sin(t * 1.5) * 0.05;
        agentRacks.forEach((rack, i) => {
          rack.position.y = -0.85 + Math.sin(t * 2 + i) * 0.04;
        });
      };

    // ─────────────────────────────────────────────────────────────
    // SCENE 2: AGENT ROUTING AND SEARCHING
    // ─────────────────────────────────────────────────────────────
    } else if (pillarIndex === 2) {
      // Top: Supervisor Intent Classifier Node
      const routerGeo = new THREE.OctahedronGeometry(0.42, 0);
      const routerMat = new THREE.MeshStandardMaterial({ color: 0x0A7E8C, metalness: 0.8, roughness: 0.2 });
      const routerNode = new THREE.Mesh(routerGeo, routerMat);
      routerNode.position.set(0, 1.05, 0);
      group.add(routerNode);

      // 4 Specialized Concurrent Search Engines
      const engines = [
        { name: "Vault", color: 0x10B981, x: -1.4, z: -0.8 },
        { name: "Network", color: 0x3B82F6, x: 1.4, z: -0.8 },
        { name: "Brain", color: 0x8B5CF6, x: -1.4, z: 0.8 },
        { name: "Forecast", color: 0xF59E0B, x: 1.4, z: 0.8 }
      ];

      const packets = [];
      engines.forEach((eng) => {
        // Platform
        const ePlat = new THREE.Mesh(
          new THREE.CylinderGeometry(0.55, 0.6, 0.25, 16),
          new THREE.MeshStandardMaterial({ color: 0x1E293B, metalness: 0.6 })
        );
        ePlat.position.set(eng.x, -0.8, eng.z);
        group.add(ePlat);

        // Core
        const eCore = new THREE.Mesh(
          new THREE.BoxGeometry(0.3, 0.35, 0.3),
          new THREE.MeshStandardMaterial({ color: eng.color, metalness: 0.7 })
        );
        eCore.position.set(eng.x, -0.5, eng.z);
        group.add(eCore);

        // Conduits from supervisor to engines
        const lineGeo = new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(0, 0.95, 0),
          new THREE.Vector3(eng.x * 0.4, 0.1, eng.z * 0.4),
          new THREE.Vector3(eng.x, -0.6, eng.z)
        ]);
        const line = new THREE.Line(lineGeo, new THREE.LineBasicMaterial({ color: eng.color, transparent: true, opacity: 0.5 }));
        group.add(line);

        // Dynamic Photon Packet
        const pkt = new THREE.Mesh(new THREE.SphereGeometry(0.08, 8, 8), new THREE.MeshBasicMaterial({ color: eng.color }));
        group.add(pkt);
        packets.push({ mesh: pkt, target: new THREE.Vector3(eng.x, -0.6, eng.z) });
      });

      animUpdate = (t) => {
        routerNode.rotation.y = t * 1.5;
        routerNode.rotation.x = t * 0.8;
        packets.forEach((p, idx) => {
          const prog = ((t * 1.2 + idx * 0.25) % 1);
          p.mesh.position.lerpVectors(new THREE.Vector3(0, 0.95, 0), p.target, prog);
        });
      };

    // ─────────────────────────────────────────────────────────────
    // SCENE 3: SYSTEM 1 APPROACH
    // ─────────────────────────────────────────────────────────────
    } else if (pillarIndex === 3) {
      // Direct 38 ms System 1 Expressway Track
      const directTrackGeo = new THREE.BoxGeometry(0.28, 0.08, 3.2);
      const directTrackMat = new THREE.MeshStandardMaterial({ color: 0x0A7E8C, metalness: 0.8 });
      const directTrack = new THREE.Mesh(directTrackGeo, directTrackMat);
      directTrack.position.set(-1.1, -0.3, 0);
      group.add(directTrack);

      // Direct Highway Laser Pulse
      const directPacketGeo = new THREE.SphereGeometry(0.14, 12, 12);
      const directPacketMat = new THREE.MeshBasicMaterial({ color: 0x22E6F0 });
      const directPacket = new THREE.Mesh(directPacketGeo, directPacketMat);
      directPacket.position.set(-1.1, -0.15, -1.4);
      group.add(directPacket);

      // Verified Output Pillar
      const goalCylGeo = new THREE.CylinderGeometry(0.35, 0.35, 0.35, 16);
      const goalCylMat = new THREE.MeshStandardMaterial({ color: 0x10B981, metalness: 0.8 });
      const goalCyl = new THREE.Mesh(goalCylGeo, goalCylMat);
      goalCyl.position.set(-1.1, -0.15, 1.4);
      group.add(goalCyl);

      // Meandering Looping Red LLM Maze Track
      const mazePoints = [
        new THREE.Vector3(0.5, -0.3, -1.4),
        new THREE.Vector3(1.4, -0.3, -1.1),
        new THREE.Vector3(0.7, -0.3, -0.5),
        new THREE.Vector3(1.5, -0.3, 0.0),
        new THREE.Vector3(0.6, -0.3, 0.5),
        new THREE.Vector3(1.3, -0.3, 0.9),
        new THREE.Vector3(0.8, -0.3, 1.4)
      ];
      const mazeCurve = new THREE.CatmullRomCurve3(mazePoints);
      const mazeTubeGeo = new THREE.TubeGeometry(mazeCurve, 32, 0.06, 8, false);
      const mazeMat = new THREE.MeshStandardMaterial({ color: 0xEF4444, roughness: 0.4 });
      const mazeTube = new THREE.Mesh(mazeTubeGeo, mazeMat);
      group.add(mazeTube);

      // Slow wandering red pulse
      const redPacketGeo = new THREE.SphereGeometry(0.1, 8, 8);
      const redPacketMat = new THREE.MeshBasicMaterial({ color: 0xF87171 });
      const redPacket = new THREE.Mesh(redPacketGeo, redPacketMat);
      group.add(redPacket);

      animUpdate = (t) => {
        // Fast laser highway
        const fastProg = (t * 2.8) % 1;
        directPacket.position.z = -1.4 + fastProg * 2.8;

        // Slow meandering maze
        const slowProg = (t * 0.3) % 1;
        const pt = mazeCurve.getPoint(slowProg);
        redPacket.position.copy(pt);
        goalCyl.rotation.y = t * 2;
      };
    }

    // Drag Interaction
    const handleMouseDown = (e) => {
      isDragging.current = true;
      mousePos.current = { x: e.clientX, y: e.clientY };
    };

    const handleMouseMove = (e) => {
      if (!isDragging.current) return;
      const dx = e.clientX - mousePos.current.x;
      const dy = e.clientY - mousePos.current.y;
      group.rotation.y += dx * 0.01;
      group.rotation.x += dy * 0.01;
      mousePos.current = { x: e.clientX, y: e.clientY };
    };

    const handleMouseUp = () => {
      isDragging.current = false;
    };

    const domElem = renderer.domElement;
    domElem.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);

    // Animation Loop
    let animFrame;
    let clock = new THREE.Clock();

    const animate = () => {
      animFrame = requestAnimationFrame(animate);
      const t = clock.getElapsedTime();

      // Subtle base auto-orbit
      if (!isDragging.current) {
        group.rotation.y += 0.003;
      }

      animUpdate(t);
      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animFrame);
      domElem.removeEventListener("mousedown", handleMouseDown);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
      renderer.dispose();
      scene.clear();
      container.innerHTML = "";
    };
  }, [pillarIndex]);

  return (
    <div className="pillar-3d-stage">
      <div ref={containerRef} className="pillar-canvas-container" />
      <div className="pillar-drag-hint">
        <RotateCcw size={10} />
        <span>Drag to rotate</span>
      </div>
    </div>
  );
}

export default function Architecture3D() {
  return (
    <div className="pillar-cards-container">
      {PILLARS_DATA.map((pillar, idx) => {
        const IconComp = pillar.icon;
        return (
          <div key={pillar.id} className="pillar-card">
            {/* Pillar Card Header - Minimal & Unboxed */}
            <div className="pillar-card-header">
              <div className="pillar-title-block">
                <div className="pillar-title-row">
                  <span className="pillar-number">{pillar.number}.</span>
                  <span className="pillar-title">{pillar.title}</span>
                </div>
                <div className="pillar-subtitle">{pillar.subtitle}</div>
              </div>
            </div>

            {/* Embedded Live 3D WebGL Simulation */}
            <SinglePillarCanvas pillarIndex={idx} />

            {/* Minimal Human-Written Information */}
            <div className="pillar-card-content">
              <p className="pillar-desc">{pillar.desc}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
