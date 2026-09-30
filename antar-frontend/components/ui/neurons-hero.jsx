"use client";

// Neural Synapse hero (reference: 01_planning/compu-ref.txt.txt) adapted for
// Antar: shown as the Brain entry/loading page. The canvas is the reference's
// CosmicSynapseCanvas verbatim (1000-neuron fibonacci sphere, mouse parallax,
// firing pulses); the copy is Antar's and the CTA enables once the real
// evidence dataset has finished loading - it is a genuine loading screen.

import React, { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { ArrowRight, BrainCircuit } from "lucide-react";

const CosmicSynapseCanvas = () => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let animationFrameId;
    let neurons = [];
    let pulses = [];
    const mouse = { x: window.innerWidth / 2, y: window.innerHeight / 2, radius: 150 };
    const perspective = 400;

    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      init();
    };

    class Neuron {
      constructor(x, y, z) {
        this.x = x; this.y = y; this.z = z;
        this.baseX = x; this.baseY = y; this.baseZ = z;
        this.radius = Math.random() * 2 + 1;
        this.activation = 0;
        this.neighbors = [];
      }
      project() {
        const rotX = (mouse.y - canvas.height / 2) * 0.0001;
        const rotY = (mouse.x - canvas.width / 2) * 0.0001;
        const cosY = Math.cos(rotY), sinY = Math.sin(rotY);
        const cosX = Math.cos(rotX), sinX = Math.sin(rotX);
        const x1 = this.x * cosY - this.z * sinY;
        const z1 = this.z * cosY + this.x * sinY;
        const y1 = this.y * cosX - z1 * sinX;
        const z2 = z1 * cosX + this.y * sinX;
        const scale = perspective / (perspective + z2);
        return { x: x1 * scale + canvas.width / 2, y: y1 * scale + canvas.height / 2, scale };
      }
      draw() {
        const { x, y, scale } = this.project();
        ctx.beginPath();
        ctx.arc(x, y, this.radius * scale, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(191, 219, 254, ${0.2 + this.activation * 0.8})`;
        ctx.fill();
      }
      update() {
        const { x: px, y: py } = this.project();
        const dx = mouse.x - px, dy = mouse.y - py;
        const dist = Math.hypot(dx, dy);
        const force = Math.max(0, (mouse.radius - dist) / mouse.radius);
        if (dist > 0) {
          this.x += (dx / dist) * force * 0.5;
          this.y += (dy / dist) * force * 0.5;
        }
        this.x += (this.baseX - this.x) * 0.01;
        this.y += (this.baseY - this.y) * 0.01;
        if (this.activation > 0) this.activation -= 0.01;
        this.draw();
      }
      fire() {
        if (this.activation > 0.5) return;
        this.activation = 1;
        this.neighbors.forEach((neighbor) => pulses.push(new Pulse(this, neighbor)));
      }
    }

    class Pulse {
      constructor(startNeuron, endNeuron) {
        this.start = startNeuron;
        this.end = endNeuron;
        this.progress = 0;
        this.speed = 0.05;
      }
      update() {
        this.progress += this.speed;
        if (this.progress >= 1) {
          this.end.activation = Math.min(1, this.end.activation + 0.5);
          return true;
        }
        return false;
      }
      draw() {
        const s = this.start.project(), e = this.end.project();
        const x = s.x + (e.x - s.x) * this.progress;
        const y = s.y + (e.y - s.y) * this.progress;
        const scale = s.scale + (e.scale - s.scale) * this.progress;
        ctx.beginPath();
        ctx.arc(x, y, 2.5 * scale, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${1 - this.progress})`;
        ctx.shadowColor = "white";
        ctx.shadowBlur = 10;
        ctx.fill();
        ctx.shadowBlur = 0;
      }
    }

    const init = () => {
      neurons = [];
      const numNeurons = 1000;
      const radius = 250;
      for (let i = 0; i < numNeurons; i++) {
        const phi = Math.acos(-1 + (2 * i) / numNeurons);
        const theta = Math.sqrt(numNeurons * Math.PI) * phi;
        neurons.push(new Neuron(
          radius * Math.cos(theta) * Math.sin(phi),
          radius * Math.sin(phi) * Math.sin(theta),
          radius * Math.cos(phi)
        ));
      }
      neurons.forEach((neuron) => {
        neurons.forEach((other) => {
          if (neuron !== other) {
            const dist = Math.hypot(neuron.x - other.x, neuron.y - other.y, neuron.z - other.z);
            if (dist < 40) neuron.neighbors.push(other);
          }
        });
      });
    };

    const animate = () => {
      ctx.fillStyle = "rgba(0, 0, 0, 0.15)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      if (Math.random() > 0.99) neurons[Math.floor(Math.random() * neurons.length)].fire();
      neurons.forEach((neuron) => neuron.update());
      pulses = pulses.filter((pulse) => !pulse.update());
      pulses.forEach((pulse) => pulse.draw());
      animationFrameId = requestAnimationFrame(animate);
    };

    const handleMouseMove = (event) => {
      mouse.x = event.clientX;
      mouse.y = event.clientY;
    };

    window.addEventListener("resize", resizeCanvas);
    window.addEventListener("mousemove", handleMouseMove);
    resizeCanvas();
    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", resizeCanvas);
      window.removeEventListener("mousemove", handleMouseMove);
    };
  }, []);

  return <canvas ref={canvasRef} className="absolute inset-0 z-0 w-full h-full bg-black" />;
};

const fadeUpVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i) => ({
    opacity: 1, y: 0,
    transition: { delay: i * 0.2 + 0.5, duration: 0.8, ease: "easeInOut" },
  }),
};

// ready  - the evidence dataset finished loading (CTA enables)
// stats  - { records } real count shown under the CTA once loaded
// onActivate - reveal the evidence brain
export default function NeuralSynapseHero({ ready = false, stats, onActivate }) {
  return (
    <div className="relative h-screen w-full flex flex-col items-center justify-center overflow-hidden">
      <CosmicSynapseCanvas />
      <div className="absolute inset-0 bg-gradient-to-t from-black via-black/50 to-transparent z-10" />

      {/* Text/CTA intentionally left blank - reserved space for future copy.
          The brain auto-launches from BrainHub after preload (6–8s). */}
      <div className="relative z-20 text-center p-6" />
    </div>
  );
}
