# Microsoft OneNote Integration Setup Guide

This guide walks you through setting up the Microsoft OneNote integration for your AI Second Brain.

> [!IMPORTANT]
> **Microsoft App Registration Requirement**
> Microsoft has deprecated the ability to register new applications using personal accounts outside of a directory tenant (Azure AD / Entra ID). 
> 
> If you are using a personal Microsoft account (like `@gmail.com` or `@outlook.com`) to store your notes on OneDrive, you will see a warning that application registration is deprecated for personal accounts.
> 
> **How to solve this:**
> * **Option A (Recommended if you have a Work/School account):** If you also have a Work/School account (e.g., `@yourcompany.com` or `@school.edu`), you can log in to Azure Portal with that account to register the application, select **Multitenant + Personal Accounts** as the supported account type, and then use your personal OneDrive account (where your active notebooks are) to log in during the device authorization flow.
> * **Option B:** Alternatively, sign up for a [Free Azure Account](https://azure.microsoft.com/free/) using your personal account. This automatically provisions a free Default Directory (tenant), allowing you to register the application.

---

## 1. Register an Application in Azure Portal

1. Open your browser and navigate to the [Microsoft Azure Portal App Registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade).
   * Sign in using your **Work/School account** (Option A) or your **Azure-enabled personal account** (Option B).
2. Click **+ New registration** at the top.
3. Configure the registration:
   * **Name**: `AI Second Brain`
   * **Supported account types**: Select **Accounts in any organizational directory (Any Microsoft Entra ID tenant - Multitenant) and personal Microsoft accounts (e.g. Skype, Xbox)**.
     * *Note: Selecting multitenant + personal accounts ensures you can sign in with your target personal Microsoft account during the authentication step, even if the app was registered under a different tenant.*
   * **Redirect URI**: Leave this blank. (We are using the Device Code Flow, which does not require a redirect URI).
4. Click **Register** at the bottom.
5. Once registered, copy the **Application (client) ID** from the Overview page. It looks like a UUID (e.g. `12345678-abcd-1234-abcd-1234567890ab`).

---

## 2. Configure Credentials

Create a `token.env` file in the skill folder: `.agent/skills/onenote-connector/token.env` and populate it with your client ID.

```env
ONENOTE_CLIENT_ID=your-copied-client-id-here
```

*(You can also specify your custom client ID in your root `.env` file as `ONENOTE_CLIENT_ID` if preferred).*

---

## 3. Run Authentication

From your terminal, run the authentication command:

```bash
python3 .agent/skills/onenote-connector/scripts/onenote_client.py --action auth
```

The script will prompt you:

```
To authenticate Microsoft OneNote, visit:
https://microsoft.com/devicelogin

And enter the code: XXXXXXXX
```

1. Open the URL `https://microsoft.com/devicelogin` in your web browser.
2. Type or paste the code shown in your terminal and click **Next**.
3. Sign in with the Microsoft account where your OneNote notebooks reside.
4. Accept the permissions request (Read/Write notes).
5. The terminal will automatically detect completion, fetch your access and refresh tokens, and save them securely to `.agent/skills/onenote-connector/token.json` (which is gitignored).

---

## 4. Configure Sync Rules (Optional)

You can customize which notebooks and section groups the system syncs by editing `.agent/skills/onenote-connector/config.json`.

```json
{
  "journal_notebook": "Personal",
  "journal_section_group": "Journal",
  "projects_notebook": "Work",
  "projects_section_group": "Projects"
}
```

* If `journal_section_group` is specified, the system will look for sections matching the current month (e.g. "Juli 2026", "2026-07") inside that group.
* If unspecified, it will search across all notebooks for a section that matches the current month name.
