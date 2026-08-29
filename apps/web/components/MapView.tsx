"use client";

import { useEffect, useRef } from "react";
import type { Hospital, Track } from "@/lib/types";

type Props = {
  phc: { lat: number; lng: number; name: string };
  hospitals?: Hospital[];
  track?: Track | null;
};

export default function MapView({ phc, hospitals = [], track }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<import("leaflet").Map | null>(null);
  const markersRef = useRef<import("leaflet").LayerGroup | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const L = await import("leaflet");
      if (cancelled || !ref.current || mapRef.current) return;
      const map = L.map(ref.current, { zoomControl: true, attributionControl: true }).setView(
        [phc.lat, phc.lng],
        13,
      );
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap",
      }).addTo(map);
      markersRef.current = L.layerGroup().addTo(map);
      mapRef.current = map;
    })();
    return () => {
      cancelled = true;
    };
  }, [phc.lat, phc.lng]);

  useEffect(() => {
    const map = mapRef.current;
    const group = markersRef.current;
    if (!map || !group) return;
    (async () => {
      const L = await import("leaflet");
      group.clearLayers();
      const phcIcon = L.divIcon({
        className: "",
        html: `<div style="background:#38bdf8;color:#001018;font-weight:700;font-size:11px;padding:4px 6px;border-radius:6px;border:1px solid #fff">PHC</div>`,
        iconSize: [36, 22],
      });
      L.marker([phc.lat, phc.lng], { icon: phcIcon }).bindPopup(phc.name).addTo(group);
      hospitals.forEach((h) => {
        const color = h.accepts_nstemi ? "#16a34a" : "#f59e0b";
        const icon = L.divIcon({
          className: "",
          html: `<div style="background:${color};color:#fff;font-size:10px;padding:3px 5px;border-radius:6px">${h.beds_icu} ICU</div>`,
          iconSize: [48, 20],
        });
        L.marker([h.lat, h.lng], { icon })
          .bindPopup(`<b>${h.name}</b><br/>${h.km} km · ICU ${h.beds_icu} · O₂ ${h.beds_oxygen}`)
          .addTo(group);
      });
      if (track) {
        const pts = (track.polyline || []).map((p) => [p.lat, p.lng] as [number, number]);
        if (pts.length) L.polyline(pts, { color: "#e11d48", weight: 3 }).addTo(group);
        const vIcon = L.divIcon({
          className: "",
          html: `<div style="background:#e11d48;color:#fff;font-size:11px;padding:4px 6px;border-radius:999px">${track.status === "arrived" ? "✓" : "🚑"}</div>`,
          iconSize: [28, 24],
        });
        L.marker([track.lat, track.lng], { icon: vIcon })
          .bindPopup(`${track.vehicle?.name || "Vehicle"} · ETA ${track.eta_min} min`)
          .addTo(group);
        map.panTo([track.lat, track.lng]);
      }
    })();
  }, [phc, hospitals, track]);

  return <div ref={ref} className="h-[280px] w-full rounded-xl bg-[#0b1220]" />;
}
