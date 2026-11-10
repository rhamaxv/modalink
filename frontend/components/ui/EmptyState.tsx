import { Icon } from "@/components/icons/Icon";

type EmptyStateAction = {
  label: string;
  onClick: () => void;
};

type EmptyStateProps = {
  /** Kalimat yang menjelaskan kenapa tampilan ini kosong, bukan label hampa. */
  reason: string;
  /** Satu aksi yang mengisi kekosongan ini. Opsional: tidak semua layar kosong punya aksi lanjutan. */
  action?: EmptyStateAction;
};

// R-27: keadaan kosong adalah bagian dari desain, bukan "Tidak ada data". Ia
// wajib menyebut sebab kekosongan dan satu aksi yang membuatnya terisi.
export function EmptyState({ reason, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-start gap-space-3 rounded-card border border-line bg-panel px-space-4 py-space-5 text-left">
      {/* Satu tanda kecil, bukan ilustrasi besar. Kotak kosong beserta
          ikonnya yang redup menyatakan "di sini seharusnya ada isi" lebih
          cepat daripada kalimatnya sendiri, tapi ilustrasi sebesar setengah
          layar hanya menunda kalimat yang justru menjelaskan sebabnya. */}
      <span className="flex h-10 w-10 items-center justify-center rounded-sm border border-line text-muted">
        <Icon name="image" size={20} />
      </span>
      <p className="max-w-measure text-body text-muted">{reason}</p>
      {action && (
        <button
          type="button"
          onClick={action.onClick}
          className="min-h-[44px] rounded-sm bg-accent px-space-3 py-space-2 text-body font-semibold text-on-accent"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
