class Theme:
    """
    Defines the application's color palette and font styles.
    """
    COLORS = {
        # Core surfaces
        'bg': '#101922',
        'card': '#1C2127',
        'card_alt': '#0D141C',
        'border': '#2A3643',

        # Brand / actions
        'primary': '#137FEC',
        'primary_hover': '#2A8CF2',
        'secondary': '#334155',
        'secondary_hover': '#475569',

        # Status
        'success': '#10B981',
        'danger': '#EF4444',
        'warning': '#F59E0B',

        # Text
        'text_dark': '#F8FAFC',
        'text_light': '#94A3B8',
        'text_muted': '#64748B',

        # Badges
        'badge_ready_bg': '#153E31',
        'badge_busy_bg': '#4A3416',
        'badge_error_bg': '#4A1B1B',
    }

    COLORS_ENTRY_BG = '#0D141C'

    FONTS = {
        'header': ("Segoe UI", 28, "bold"),
        'subheader': ("Segoe UI", 11),
        'label': ("Segoe UI", 10),
        'label_bold': ("Segoe UI", 10, "bold"),
        'button': ("Segoe UI", 10, "bold"),
        'icon_large': ("Segoe UI", 24, "bold"),
        'icon_medium': ("Segoe UI", 12, "bold"),
        'code': ("Consolas", 10),
        'dialog_title': ("Segoe UI", 14, "bold"),
        'dialog_label': ("Segoe UI", 10),
        'dialog_small': ("Segoe UI", 9),
        'dialog_help': ("Segoe UI", 8),
        'card_title': ("Segoe UI", 12, "bold"),
        'section': ("Segoe UI", 9, "bold"),
        'footer': ("Segoe UI", 8, "bold"),
    }
