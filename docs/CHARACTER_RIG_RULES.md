# Character Rig Rules (SVG -> Lottie/Runtime)

1. Build hierarchy by semantics, not by paint order: `character -> part -> subpart -> detail`.
2. Every movable limb is a standalone object with stable `id`.
3. Use layered construction per object: `fill`, `shadow`, `highlight`, `details`.
4. Define one local pivot per movable object (joint anchor) and animate around it.
5. Keep style local to each object; avoid shared styling that couples unrelated parts.
6. Separate deformation from decoration: base shape can bend, details follow via local transform.
7. Keep topological stability: object path point count should stay constant across keyframes.
8. Use rig metadata (`data-rig`, `data-part`, `data-pivot`) for tooling and AI pipelines.
9. Face elements (eyes/mouth) are independent controls, never fused into head shape.
10. Provide fallback render profile: simplified geometry for mobile/low-power targets.
