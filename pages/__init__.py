"""Page objects package."""

from .appeals_page import AppealsPage
from .base_page import BasePage
from .claim_status_page import ClaimStatusPage
from .dashboard_page import DashboardPage
from .eligibility_page import EligibilityPage
from .login_page import LoginPage

__all__ = ["BasePage", "LoginPage", "DashboardPage", "EligibilityPage", "ClaimStatusPage", "AppealsPage"]

