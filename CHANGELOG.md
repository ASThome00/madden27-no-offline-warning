# Changelog

## 1.0 – 2026-08-29
- Initial release. Removes the **"ACCOUNT ERROR"** login-failure popup (the one MMC fills with *"Mods require being offline… -MMC/CFMC"*) that appears at boot and again whenever a mode re-runs the sign-in while signed out.
  One one-byte patch in `common/ui/node_com/scriptpod.ast` (`madden.online.module.Login._ShowLoginFailedPopup`).
- Note: while the mod is active, *any* login-failure popup from that class is suppressed (the login-failed callback still runs, so menus continue exactly as if you had pressed OK).
