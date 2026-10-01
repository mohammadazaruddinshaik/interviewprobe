/** Atmosphere only: deep forest-to-ink gradient, soft light behind the presence, two very slow organic shapes. */
function RoomBackdrop() {
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-0 overflow-hidden bg-[#06110a]">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_70%_55%_at_50%_18%,rgb(36_64_26/0.75),transparent_70%),radial-gradient(ellipse_90%_60%_at_50%_110%,rgb(3_35_30/0.8),transparent_70%)]" />
      <div className="ip-motion absolute -left-[12%] top-[30%] h-[46vmax] w-[46vmax] animate-[ip-float_46s_ease-in-out_infinite] rounded-[46%_54%_58%_42%/52%_44%_56%_48%] bg-forest-light/25 blur-3xl" />
      <div className="ip-motion absolute -right-[14%] top-[2%] h-[38vmax] w-[38vmax] animate-[ip-float_58s_ease-in-out_8s_infinite] rounded-[58%_42%_44%_56%/46%_58%_42%_54%] bg-deep/60 blur-3xl" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_55%,rgb(0_0_0/0.45))]" />
    </div>
  )
}

export default RoomBackdrop
