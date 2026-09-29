import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Navigation } from "./Navigation";
import { Hero } from "./Hero";
import { ExperienceStrip } from "./ExperienceStrip";

gsap.registerPlugin(ScrollTrigger);

const A = "/assets/interviewprobe-landing";

export function LandingPage() {
  const pageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = pageRef.current;
    if (!el) return;

    const prefersReduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    if (prefersReduced) {
      el.querySelectorAll("[data-anim]").forEach((node) => {
        gsap.set(node, { autoAlpha: 1 });
      });
      return;
    }

    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

      tl.from("[data-anim='nav']", {
        autoAlpha: 0,
        y: -18,
        duration: 0.6,
      })
        .from(
          "[data-anim='headline']",
          { autoAlpha: 0, y: 30, duration: 0.7 },
          "-=0.3",
        )
        .from(
          "[data-anim='highlight']",
          {
            scaleX: 0,
            transformOrigin: "left center",
            duration: 0.5,
          },
          "-=0.2",
        )
        .from(
          "[data-anim='portrait']",
          { autoAlpha: 0, y: 40, rotation: -4, duration: 0.7 },
          "-=0.3",
        )
        .from(
          "[data-anim='copy']",
          { autoAlpha: 0, y: 20, duration: 0.5 },
          "-=0.4",
        )
        .from(
          "[data-anim='cta']",
          { autoAlpha: 0, y: 20, duration: 0.5 },
          "-=0.3",
        )
        .from(
          "[data-anim='annotation']",
          {
            autoAlpha: 0,
            scale: 0.85,
            rotation: "random(-8, 8)",
            duration: 0.4,
            stagger: 0.08,
          },
          "-=0.3",
        )
        .from(
          "[data-anim='card']",
          {
            autoAlpha: 0,
            y: 30,
            duration: 0.5,
            stagger: 0.1,
          },
          "-=0.4",
        )
        .from(
          "[data-anim='social']",
          { autoAlpha: 0, y: 16, duration: 0.4 },
          "-=0.2",
        );

      ScrollTrigger.batch("[data-anim='strip-col']", {
        onEnter: (batch) =>
          gsap.from(batch, {
            autoAlpha: 0,
            y: 40,
            duration: 0.6,
            stagger: 0.12,
            ease: "power2.out",
          }),
        start: "top 85%",
        once: true,
      });
    }, el);

    return () => ctx.revert();
  }, []);

  return (
    <div ref={pageRef} className="relative min-h-screen overflow-x-hidden">
      {/* ─── BACKGROUND LAYERS ─── */}
      <div
        className="pointer-events-none fixed inset-0 -z-10"
        aria-hidden="true"
      >
        <div className="absolute inset-0 bg-cream" />
        <div
          className="absolute inset-0 opacity-[0.05]"
          style={{
            backgroundImage: `url(${A}/backgrounds/paper-texture.png)`,
            backgroundSize: "600px",
          }}
        />
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage: `url(${A}/backgrounds/grid.png)`,
            backgroundSize: "300px",
          }}
        />
        <div
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: `url(${A}/backgrounds/dots.png)`,
            backgroundSize: "200px",
          }}
        />
        <img
          src={`${A}/backgrounds/corner-hatch.png`}
          alt=""
          className="absolute right-0 top-0 w-44 opacity-[0.22] lg:w-60"
        />
      </div>

      {/* ─── PAGE CONTENT ─── */}
      <Navigation />
      <Hero />
      <ExperienceStrip />
    </div>
  );
}
