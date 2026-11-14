"""Engine deterministik untuk seluruh test dan untuk demo tanpa jaringan (D-07).

Penanda [[SCORE:n]] dan [[RED_FLAG:level]] hanya dikenali di sini,
tidak pernah dikirim ke Gemini.

Penandanya dibaca dari `document.extracted_text`, bukan dari field di
formulir: sejak uraian proposal pindah ke PDF, di situlah satu-satunya tempat
teks sepanjang itu bisa tinggal. Test yang ingin memaksa skor menyiapkan
dokumen yang teksnya memuat penanda, bukan mengetiknya ke ringkasan.
"""

import re
from collections.abc import Sequence

from app.ai.engine import CampaignLike, DocumentLike, MilestoneLike, ProposalLike
from app.ai.models import Brief, ProposalScore, RedFlag

PENANDA_SKOR = re.compile(r"\[\[SCORE:(\d+)\]\]")
PENANDA_FLAG = re.compile(r"\[\[RED_FLAG:(info|warning|critical)\]\]")


class MockScoringEngine:
    name = "mock"
    model = "mock-v1"

    async def score(
        self,
        proposal: ProposalLike,
        campaign: CampaignLike,
        document: DocumentLike,
        milestones: Sequence[MilestoneLike],
    ) -> ProposalScore:
        # Ringkasan ikut dibaca, bukan dokumen saja: sebagian test lebih
        # mudah ditulis dengan menaruh penanda di ringkasan yang pendek
        # daripada menyusun PDF hanya untuk satu angka.
        teks = f"{proposal.business_summary}\n{document.extracted_text}"

        flags = [
            RedFlag(
                code="penanda_uji",
                severity=level,
                message="Dipicu penanda uji.",
                evidence=f"[[RED_FLAG:{level}]]",
            )
            for level in PENANDA_FLAG.findall(teks)
        ]

        if paksa := PENANDA_SKOR.search(teks):
            total = min(int(paksa.group(1)), 100)
            fit = min(total, 40)
            data = min(total - fit, 30)
            return ProposalScore(
                fit_score=fit,
                data_quality_score=data,
                impact_score=total - fit - data,
                red_flags=flags,
                brief=self._brief(proposal),
            )

        # Skor dasar dari kelengkapan dokumen, dibatasi rentangnya. Kecocokan
        # diukur dari porsi dana yang diminta terhadap target campaign, bukan
        # dari sektor: Proposal tidak punya kolom sector, hanya Campaign yang
        # punya, sehingga membandingkan keduanya melempar AttributeError
        # begitu baris Proposal sungguhan masuk (lihat plan fase ini).
        porsi = proposal.requested_amount / campaign.target_amount
        fit = 40 if porsi <= 0.5 else (30 if porsi <= 0.8 else 22)
        # Panjang teks dokumen dan jumlah tahap, bukan panjang dua textarea
        # yang sudah tidak ada. Dibagi 40, bukan 10, karena dokumen sungguhan
        # jauh lebih panjang daripada field formulir yang digantikannya, dan
        # pembagi lama membuat hampir semua dokumen langsung menyentuh batas
        # atas sehingga skornya berhenti membedakan apa pun.
        data = min(len(document.extracted_text) // 40, 30)
        impact = min(len(milestones) * 8, 30)
        return ProposalScore(
            fit_score=fit,
            data_quality_score=data,
            impact_score=impact,
            red_flags=flags,
            brief=self._brief(proposal),
        )

    def _brief(self, proposal: ProposalLike) -> Brief:
        return Brief(
            strengths=[f"Profil usaha {proposal.business_name} terisi."],
            risks=["Penilaian ini berasal dari engine tiruan, bukan dari model AI."],
            recommendation="Gunakan hanya untuk pengujian.",
        )
