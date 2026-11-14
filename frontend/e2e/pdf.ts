/**
 * Penghasil PDF satu halaman untuk e2e.
 *
 * Ditulis tangan, tanpa pustaka, dengan alasan yang sama seperti padanannya
 * di backend/app/seed/pdf.py: satu-satunya pemakainya adalah test, dan
 * menarik pustaka PDF beserta rantai dependency-nya ke dalam frontend demi
 * beberapa berkas uji bukan pertukaran yang sebanding.
 *
 * Ada satu berkas tetap di e2e/fixtures/proposal-e2e.pdf untuk skenario yang
 * isinya tidak berubah. Fungsi ini untuk yang berubah: alur-pasar membuat
 * beberapa proposal dengan penanda skor berbeda, dan menyiapkan satu berkas
 * tetap per angka berarti menambah berkas setiap kali skenarionya tumbuh.
 *
 * Alirannya sengaja tidak dikompres. PDF mengizinkannya, pypdf di server
 * membacanya apa adanya, dan tanpa kompresi berkas ini bisa dibaca mata
 * manusia saat sebuah test gagal dan seseorang perlu tahu apa isinya.
 */

function escapeTeks(teks: string): string {
  // Kurung dan backslash adalah sintaks literal string di dalam aliran isi
  // PDF. Satu tanda kurung dalam teks Indonesia sudah cukup membuat seluruh
  // berkas gagal diurai.
  return teks.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
}

function bungkus(teks: string, lebar = 88): string[] {
  const hasil: string[] = [];
  let baris = "";
  for (const kata of teks.split(/\s+/)) {
    if (!baris) baris = kata;
    else if (baris.length + 1 + kata.length <= lebar) baris = `${baris} ${kata}`;
    else {
      hasil.push(baris);
      baris = kata;
    }
  }
  if (baris) hasil.push(baris);
  return hasil;
}

export function buatPdf(judul: string, isi: string): Buffer {
  const baris = [judul.toUpperCase(), "", ...bungkus(isi)];
  const aliran =
    `BT /F1 11 Tf 50 780 Td 15 TL\n` +
    baris.map((b) => `(${escapeTeks(b)}) Tj T*`).join("\n") +
    `\nET`;

  const objek = [
    `<< /Type /Catalog /Pages 2 0 R >>`,
    `<< /Type /Pages /Kids [3 0 R] /Count 1 >>`,
    `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] ` +
      `/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>`,
    `<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>`,
    `<< /Length ${Buffer.byteLength(aliran, "latin1")} >>\nstream\n${aliran}\nendstream`,
  ];

  let keluaran = "%PDF-1.4\n";
  const posisi: number[] = [];
  objek.forEach((o, i) => {
    posisi.push(Buffer.byteLength(keluaran, "latin1"));
    keluaran += `${i + 1} 0 obj\n${o}\nendobj\n`;
  });

  const awalXref = Buffer.byteLength(keluaran, "latin1");
  keluaran += `xref\n0 ${objek.length + 1}\n0000000000 65535 f \n`;
  for (const p of posisi) keluaran += `${String(p).padStart(10, "0")} 00000 n \n`;
  keluaran += `trailer\n<< /Size ${objek.length + 1} /Root 1 0 R >>\nstartxref\n${awalXref}\n%%EOF\n`;

  return Buffer.from(keluaran, "latin1");
}
