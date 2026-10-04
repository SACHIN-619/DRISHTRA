/* A small, dependency-free motion layer (scroll reveals, scroll-linked progress,
   split-word reveals, count-ups, tilt). Same ideas as framer-motion's useInView /
   useScroll, kept local so the console builds and runs fully offline.
   Honours prefers-reduced-motion. */
import { Fragment, useEffect, useRef, useState } from "react";

export const reducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export function useInView<T extends Element>(opts: { once?: boolean; threshold?: number; rootMargin?: string } = {}) {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (reducedMotion() || typeof IntersectionObserver === "undefined") { setInView(true); return; }
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setInView(true); if (opts.once !== false) io.disconnect(); }
      else if (opts.once === false) setInView(false);
    }, { threshold: opts.threshold ?? 0.18, rootMargin: opts.rootMargin ?? "0px 0px -8% 0px" });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return { ref, inView };
}

export function Reveal({ children, delay = 0, y = 28, className = "", as: Tag = "div", style }: {
  children: React.ReactNode; delay?: number; y?: number; className?: string; as?: any; style?: React.CSSProperties;
}) {
  const { ref, inView } = useInView<HTMLDivElement>();
  return (
    <Tag ref={ref} className={`rv ${inView ? "in" : ""} ${className}`}
      style={{ ...style, transitionDelay: `${delay}ms`, ["--rv-y" as any]: `${y}px` }}>
      {children}
    </Tag>
  );
}

/** Word-by-word reveal; wrap a span with className "hl" to highlight words. */
export function SplitWords({ text, highlight = [], className = "", stagger = 55, base = 0 }: {
  text: string; highlight?: string[]; className?: string; stagger?: number; base?: number;
}) {
  const { ref, inView } = useInView<HTMLSpanElement>({ threshold: 0.3 });
  const words = text.split(" ");
  const hl = new Set(highlight.map(h => h.toLowerCase().replace(/[^a-z0-9-]/g, "")));
  return (
    <span ref={ref} className={`split ${inView ? "in" : ""} ${className}`}>
      {words.map((w, i) => (
        <Fragment key={i}>
          <span className="w">
            <span className={hl.has(w.toLowerCase().replace(/[^a-z0-9-]/g, "")) ? "hl" : ""} style={{ transitionDelay: `${base + i * stagger}ms` }}>{w}</span>
          </span>
          {i < words.length - 1 ? " " : ""}
        </Fragment>
      ))}
    </span>
  );
}

/** 0..1 progress of the viewport through a tall (sticky) section. */
export function useScrollProgress<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [p, setP] = useState(0);
  useEffect(() => {
    let raf = 0;
    const tick = () => {
      raf = 0;
      const el = ref.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const total = r.height - window.innerHeight;
      const v = total > 0 ? Math.min(1, Math.max(0, -r.top / total)) : (r.top < window.innerHeight ? 1 : 0);
      setP(v);
    };
    const on = () => { if (!raf) raf = requestAnimationFrame(tick); };
    tick();
    window.addEventListener("scroll", on, { passive: true });
    window.addEventListener("resize", on);
    return () => { window.removeEventListener("scroll", on); window.removeEventListener("resize", on); cancelAnimationFrame(raf); };
  }, []);
  return { ref, p };
}

/** Global page scroll 0..1 (for the top progress bar). */
export function usePageProgress() {
  const [p, setP] = useState(0);
  useEffect(() => {
    const on = () => {
      const h = document.documentElement.scrollHeight - window.innerHeight;
      setP(h > 0 ? window.scrollY / h : 0);
    };
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  return p;
}

export function CountUp({ to, duration = 1400, suffix = "", decimals = 0 }: { to: number; duration?: number; suffix?: string; decimals?: number }) {
  const { ref, inView } = useInView<HTMLSpanElement>({ threshold: 0.5 });
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!inView) return;
    if (reducedMotion()) { setV(to); return; }
    const t0 = performance.now();
    let raf = 0;
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / duration);
      const eased = 1 - Math.pow(1 - k, 3);
      setV(to * eased);
      if (k < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [inView, to, duration]);
  return <span ref={ref}>{v.toFixed(decimals)}{suffix}</span>;
}

/** Subtle 3D tilt that follows the pointer. */
export function Tilt({ children, className = "", max = 8 }: { children: React.ReactNode; className?: string; max?: number }) {
  const ref = useRef<HTMLDivElement | null>(null);
  const onMove = (e: React.MouseEvent) => {
    const el = ref.current;
    if (!el || reducedMotion()) return;
    const r = el.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5;
    const y = (e.clientY - r.top) / r.height - 0.5;
    el.style.transform = `perspective(1100px) rotateY(${x * max}deg) rotateX(${-y * max}deg)`;
    el.style.setProperty("--gx", `${(x + 0.5) * 100}%`);
    el.style.setProperty("--gy", `${(y + 0.5) * 100}%`);
  };
  const reset = () => { if (ref.current) ref.current.style.transform = "perspective(1100px) rotateY(0) rotateX(0)"; };
  return <div ref={ref} className={`tilt ${className}`} onMouseMove={onMove} onMouseLeave={reset}>{children}</div>;
}

/** Pointer-following glow position for a container (sets --mx/--my). */
export function usePointerGlow<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || reducedMotion()) return;
    const on = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      el.style.setProperty("--mx", `${e.clientX - r.left}px`);
      el.style.setProperty("--my", `${e.clientY - r.top}px`);
    };
    el.addEventListener("pointermove", on);
    return () => el.removeEventListener("pointermove", on);
  }, []);
  return ref;
}
