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
    <div className="flex flex-col items-start gap-space-3 rounded-card border border-line bg-surface px-space-4 py-space-5 text-left">
      <p className="max-w-measure text-base leading-[1.6] text-muted">{reason}</p>
      {action && (
        <button
          type="button"
          onClick={action.onClick}
          className="min-h-[44px] rounded-sm bg-accent px-space-3 py-space-2 text-base leading-[1.6] font-semibold text-ink"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
