"""Limites des documents enregistrés, sans période ni compteur supplémentaire."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UsagePolicy:
    max_pdf: int
    max_pdf_pages: int
    max_images: int


FREE_POLICY = UsagePolicy(max_pdf=2, max_pdf_pages=5, max_images=3)
PAID_POLICY = UsagePolicy(max_pdf=10, max_pdf_pages=30, max_images=15)


def get_usage_policy(user):
    """Choisir les limites de l'utilisateur authentifié à chaque requête."""
    return PAID_POLICY if user.state_abonnement else FREE_POLICY
