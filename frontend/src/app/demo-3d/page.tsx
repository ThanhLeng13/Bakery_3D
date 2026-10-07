"use client";

/**
 * TRANG DEMO TẠM — để đối chiếu "trước / sau" khi nâng cấp 3D.
 * Xoá trang này sau khi chốt phương án.
 *
 * Bên trái  : mô phỏng ĐÚNG cách Cake3D.tsx đang dựng bánh hiện nay
 *             (hình trụ + màu cam san hô #E8837A + đèn ấm + vật liệu nhám).
 * Bên phải  : cùng dữ liệu nhưng nạp từ file .glb + vật liệu PBR + studio light.
 *
 * Hai bên dùng CÙNG một khung hình, cùng góc máy -> khác biệt nhìn thấy được
 * là do vật liệu / ánh sáng / model, không phải do góc chụp.
 */

import { Suspense, useMemo } from "react";
import * as THREE from "three";
import { Canvas } from "@react-three/fiber";
import {
  ContactShadows,
  Environment,
  Lightformer,
  OrbitControls,
  useGLTF,
} from "@react-three/drei";

type ZoneKey = "body" | "top" | "border" | "stand";

const DEFAULT_COLORS: Record<ZoneKey, string> = {
  body: "#EFE7DA",
  top: "#FFFFFF",
  border: "#FAF6EF",
  stand: "#DCD8D1",
};

/** Mỗi vùng một kiểu vật liệu — kem phủ bóng gắt, thân mờ hơn. */
const ZONE_STYLE: Record<ZoneKey, { roughness: number; clearcoat: number; clearcoatRoughness: number }> = {
  body: { roughness: 0.44, clearcoat: 0.55, clearcoatRoughness: 0.22 },
  top: { roughness: 0.09, clearcoat: 1.0, clearcoatRoughness: 0.03 },
  border: { roughness: 0.15, clearcoat: 1.0, clearcoatRoughness: 0.07 },
  stand: { roughness: 0.5, clearcoat: 0.25, clearcoatRoughness: 0.4 },
};

function zoneOf(name: string): ZoneKey | null {
  if (name.startsWith("Body")) return "body";
  if (name.startsWith("Top")) return "top";
  if (name.startsWith("Border")) return "border";
  if (name.startsWith("Stand")) return "stand";
  return null;
}

/** Nạp file .glb rồi thay vật liệu theo TÊN VÙNG -> giữ được tính năng tô màu theo vùng. */
function CakeModel({
  url,
  colors = DEFAULT_COLORS,
}: {
  url: string;
  colors?: Record<ZoneKey, string>;
}) {
  const { scene } = useGLTF(url);

  const model = useMemo(() => {
    const clone = scene.clone(true);
    clone.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (!mesh.isMesh) return;
      const zone = zoneOf(mesh.name);
      if (!zone) return;
      const style = ZONE_STYLE[zone];
      mesh.material = new THREE.MeshPhysicalMaterial({
        color: new THREE.Color(colors[zone]),
        metalness: 0.0,
        roughness: style.roughness,
        clearcoat: style.clearcoat,
        clearcoatRoughness: style.clearcoatRoughness,
      });
      mesh.castShadow = true;
      mesh.receiveShadow = true;
    });
    return clone;
  }, [scene, colors]);

  return <primitive object={model} />;
}

/** Ánh sáng studio: khoảng sáng mềm dựng bằng Lightformer, KHÔNG cần tải file HDR.
 *  Cần cả nguồn LỚN (ánh sáng nền) lẫn nguồn NHỎ cường độ cao (đốm bóng gắt trên kem). */
function Studio({ shadow = true }: { shadow?: boolean }) {
  return (
    <>
      <ambientLight intensity={0.22} />
      <directionalLight
        position={[3.2, 5.2, 3.4]}
        intensity={1.5}
        castShadow={shadow}
        shadow-mapSize={[1024, 1024]}
        shadow-bias={-0.0004}
      />
      <directionalLight position={[-4, 1.6, -2.2]} intensity={0.5} color="#EAF0FF" />
      <Environment resolution={256}>
        {/* nguồn lớn, mềm -> ánh sáng nền */}
        <Lightformer form="rect" intensity={2.0} position={[0, 5, -6]} scale={[11, 11, 1]} color="#ffffff" />
        <Lightformer form="rect" intensity={1.1} position={[-6.5, 1.5, 1]} scale={[9, 9, 1]} color="#ffffff" />
        <Lightformer form="rect" intensity={0.9} position={[6.5, 2, 1]} scale={[9, 9, 1]} color="#fff3e4" />
        {/* nguồn NHỎ, mạnh -> đốm bóng gắt, làm kem trông bóng ướt */}
        <Lightformer form="circle" intensity={9} position={[1.7, 3.4, 2.6]} scale={0.75} color="#ffffff" />
        <Lightformer form="circle" intensity={5} position={[-2.4, 2.6, 2.0]} scale={0.6} color="#ffffff" />
        <Lightformer form="circle" intensity={4} position={[0, -3, 2]} scale={5} color="#ffffff" />
      </Environment>
      {shadow ? (
        <ContactShadows position={[0, 0.001, 0]} opacity={0.45} scale={6} blur={2.4} far={3} color="#2B2B2A" />
      ) : null}
    </>
  );
}

/** Mô phỏng ĐÚNG cách hiện tại: hình trụ + màu san hô + vật liệu nhám + đèn ấm. */
function LegacyCake() {
  return (
    <>
      <ambientLight intensity={1.0} />
      <directionalLight color="#FFFAF0" intensity={1.5} position={[3, 5, 3]} />
      <directionalLight color="#FFD0C0" intensity={0.6} position={[-4, 2, -2]} />
      <directionalLight color="#FFF0E8" intensity={0.3} position={[0, -3, 2]} />
      <pointLight color="#FFFBF0" intensity={0.8} position={[0, 2, 3]} />

      <group>
        <mesh position={[0, 0.15, 0]}>
          <cylinderGeometry args={[0.5, 0.5, 0.3, 48]} />
          <meshStandardMaterial color="#E8837A" roughness={0.45} />
        </mesh>
        <mesh position={[0, 0.305, 0]}>
          <torusGeometry args={[0.5, 0.02, 10, 48]} />
          <meshStandardMaterial color="#D9A94A" roughness={0.4} metalness={0.3} />
        </mesh>
        {[0, 1, 2, 3, 4].map((i) => {
          const a = (i / 5) * Math.PI * 2;
          return (
            <mesh key={i} position={[Math.cos(a) * 0.3, 0.36, Math.sin(a) * 0.3]}>
              <sphereGeometry args={[0.07, 16, 12]} />
              <meshStandardMaterial color="#FFFFFF" roughness={0.5} />
            </mesh>
          );
        })}
      </group>
    </>
  );
}

const CAMERA = { position: [1.32, 0.82, 1.72] as [number, number, number], fov: 34 };

/** Nền studio: gradient nhẹ để bánh trắng không chìm vào nền trắng. */
const BACKDROP =
  "radial-gradient(125% 95% at 50% 0%, #FFFFFF 0%, #F6F4F0 50%, #E6E3DC 100%)";

function Panel({
  title,
  subtitle,
  tone,
  children,
}: {
  title: string;
  subtitle: string;
  tone: "old" | "new";
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col overflow-hidden rounded-2xl border border-line bg-surface">
      <div
        className={
          "flex items-baseline justify-between gap-3 border-b px-4 py-3 " +
          (tone === "old"
            ? "border-line bg-[#FDF3F1]"
            : "border-line bg-[#F4F6F4]")
        }
      >
        <span className="font-serif text-base font-semibold text-ink">{title}</span>
        <span className="text-[11px] uppercase tracking-[0.14em] text-muted">{subtitle}</span>
      </div>
      <div className="aspect-square w-full" style={{ background: BACKDROP }}>
        {children}
      </div>
    </div>
  );
}

/** Bày 6 mẫu cạnh nhau để cho thấy "kho mẫu 3D". */
function Gallery() {
  const items = [
    "/models/cake-tron-1-tang.glb",
    "/models/cake-tron-2-tang.glb",
    "/models/cake-tron-3-tang.glb",
    "/models/cake-vuong-1-tang.glb",
    "/models/cake-trai-tim.glb",
    "/models/cake-cao-1-tang.glb",
  ];
  return (
    <>
      {items.map((url, i) => {
        const col = i % 3;
        const row = Math.floor(i / 3);
        return (
          <group
            key={url}
            position={[(col - 1) * 1.55, 0, row === 0 ? 0.85 : -0.75]}
            scale={0.95}
          >
            <CakeModel url={url} />
          </group>
        );
      })}
    </>
  );
}

/** Ba bảng màu khác nhau — chứng minh tô màu theo vùng vẫn chạy trên model .glb. */
function Colorways() {
  const ways: Array<Record<ZoneKey, string>> = [
    { body: "#EFE7DA", top: "#FFFFFF", border: "#FAF6EF", stand: "#DCD8D1" },
    { body: "#DCC6A6", top: "#F7EBD8", border: "#C9AC85", stand: "#DCD8D1" },
    { body: "#B98CA4", top: "#F2E2EC", border: "#E3C6D6", stand: "#DCD8D1" },
  ];
  return (
    <>
      {ways.map((colors, i) => (
        <group key={i} position={[(i - 1) * 1.6, 0, 0]}>
          <CakeModel url="/models/cake-tron-1-tang.glb" colors={colors} />
        </group>
      ))}
    </>
  );
}

export default function Demo3DPage() {
  return (
    <main className="mx-auto max-w-[1280px] px-6 py-10">
      <p className="text-[11px] uppercase tracking-[0.2em] text-muted">Bản thử — chưa đụng vào code chính</p>
      <h1 className="mt-2 font-serif text-3xl font-semibold text-ink">
        Nâng cấp mô hình bánh 3D
      </h1>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted">
        Bên trái là cách dựng hiện tại. Bên phải là cùng chiếc bánh nhưng nạp từ file{" "}
        <code className="rounded bg-canvas px-1 py-0.5 text-[12px]">.glb</code> tự sinh, dùng vật liệu
        PBR có lớp bóng (clearcoat) và ánh sáng studio. Cả hai dùng chung một góc máy.
      </p>

      <section className="mt-8 grid gap-6 md:grid-cols-2">
        <Panel title="Hiện tại" subtitle="Hình trụ · nhám · đèn ấm" tone="old">
          <Canvas camera={CAMERA} dpr={[1, 2]} gl={{ antialias: true, alpha: true }} shadows>
            <Suspense fallback={null}>
              <LegacyCake />
            </Suspense>
            <OrbitControls
              target={[0, 0.22, 0]}
              enablePan={false}
              minDistance={1.4}
              maxDistance={5}
              maxPolarAngle={Math.PI / 2.05}
            />
          </Canvas>
        </Panel>

        <Panel title="Sau khi nâng cấp" subtitle=".glb · PBR bóng · studio" tone="new">
          <Canvas camera={CAMERA} dpr={[1, 2]} gl={{ antialias: true, alpha: true }} shadows>
            <Suspense fallback={null}>
              <Studio />
              <CakeModel url="/models/cake-tron-1-tang.glb" />
            </Suspense>
            <OrbitControls
              target={[0, 0.22, 0]}
              enablePan={false}
              minDistance={1.4}
              maxDistance={5}
              maxPolarAngle={Math.PI / 2.05}
            />
          </Canvas>
        </Panel>
      </section>

      <section className="mt-10">
        <h2 className="font-serif text-xl font-semibold text-ink">Kho mẫu 3D — 6 kiểu</h2>
        <p className="mt-1 text-sm text-muted">
          Mỗi file vài trăm KB, đều có đủ 3 vùng <code className="rounded bg-canvas px-1">Body</code>{" "}
          <code className="rounded bg-canvas px-1">Top</code>{" "}
          <code className="rounded bg-canvas px-1">Border</code> để tô màu.
        </p>
        <div className="mt-4 h-[430px] overflow-hidden rounded-2xl border border-line" style={{ background: BACKDROP }}>
          <Canvas camera={{ position: [0, 2.15, 3.6], fov: 36 }} dpr={[1, 2]} gl={{ antialias: true, alpha: true }} shadows>
            <Suspense fallback={null}>
              <Studio shadow={false} />
              <Gallery />
            </Suspense>
            <OrbitControls target={[0, 0.48, 0.05]} enablePan={false} minDistance={2.5} maxDistance={11} maxPolarAngle={Math.PI / 2.1} />
          </Canvas>
        </div>
      </section>

      <section className="mt-10">
        <h2 className="font-serif text-xl font-semibold text-ink">Tô màu theo vùng vẫn hoạt động</h2>
        <p className="mt-1 text-sm text-muted">
          Cùng một file <code className="rounded bg-canvas px-1">.glb</code>, chỉ đổi màu từng vùng —
          đúng tính năng &ldquo;thiết kế bánh trực quan theo vùng&rdquo;.
        </p>
        <div className="mt-4 h-[370px] overflow-hidden rounded-2xl border border-line" style={{ background: BACKDROP }}>
          <Canvas camera={{ position: [0, 1.35, 2.9], fov: 36 }} dpr={[1, 2]} gl={{ antialias: true, alpha: true }} shadows>
            <Suspense fallback={null}>
              <Studio shadow={false} />
              <Colorways />
            </Suspense>
            <OrbitControls target={[0, 0.28, 0]} enablePan={false} minDistance={2} maxDistance={9} maxPolarAngle={Math.PI / 2.1} />
          </Canvas>
        </div>
      </section>

      <p className="mt-10 rounded-xl border border-line bg-canvas p-4 text-xs leading-relaxed text-muted">
        Đây là bản thử để bạn xem trước. Model do script{" "}
        <code className="rounded bg-surface px-1">scripts/generate-cake-models.js</code> sinh ra, không tải từ
        mạng. Khi bạn đồng ý, tôi mới đưa vào <code className="rounded bg-surface px-1">/cake-builder</code> và{" "}
        <code className="rounded bg-surface px-1">Cake3D.tsx</code>.
      </p>
    </main>
  );
}
