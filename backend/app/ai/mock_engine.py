"""Engine deterministik untuk seluruh test dan untuk demo tanpa jaringan (D-07).

Penanda [[SCORE:n]] dan [[RED_FLAG:level]] hanya dikenali di sini,
tidak pernah dikirim ke Gemini.
"""

import re

from app.ai.models import Brief, ProposalScore, RedFlag

PENANDA_SKOR = re.compile(r"\[\[SCORE:(\d+)\]\]")
PENANDA_FLAG = re.compile(r"\[\[RED_FLAG:(info|warning|critical)\]\]")


class MockScoringEngine:
    name = "mock"
    model = "mock-v1"

    async def score(self, proposal, campaign) -> ProposalScore:
        # f-string, bukan " ".join([...]) seperti di draft brief: isinya sama,
        # tapi gerbang ruff proyek ini menandai join daftar literal (FLY002).
        teks = (
            f"{proposal.business_profile} {proposal.fund_usage_plan} "
            f"{proposal.business_projection}"
        )

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

        # Skor dasar dari kelengkapan isian, dibatasi rentangnya.
        fit = 40 if proposal.sector == campaign.sector else 22
        data = min(len(proposal.fund_usage_plan) // 10, 30)
        impact = min(len(proposal.business_projection) // 10, 30)
        return ProposalScore(
            fit_score=fit,
            data_quality_score=data,
            impact_score=impact,
            red_flags=flags,
            brief=self._brief(proposal),
        )

    def _brief(self, proposal) -> Brief:
        return Brief(
            strengths=[f"Profil usaha {proposal.business_name} terisi."],
            risks=["Penilaian ini berasal dari engine tiruan, bukan dari model AI."],
            recommendation="Gunakan hanya untuk pengujian.",
        )
