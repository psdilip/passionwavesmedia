---
title: Getting Chrome onto Windows Server 2019
slug: download-chrome-ie-windows-server-2019
category: How-To
tags: Windows Server, Internet Explorer, Chrome
excerpt: A fresh Windows Server 2019 box only comes with Internet Explorer — here's how to get Chrome onto it without a fight.
date: 2022-02-17
---

A new Windows Server 2019 instance only ships with Internet Explorer, and IE's default security settings actively get in the way of downloading anything — including the browser you'd rather be using. Here's the sequence that gets Chrome installed without fighting it the whole way.

1. When IE opens for the first time, dismiss the initial pop-up with **OK**.
2. Open **Internet Options** from the settings menu.
3. Go to the **Security** tab.
4. Click **Custom Level**, find the **Downloads** section, and enable **File Download**.
5. Click **OK** and confirm the security-settings change when it asks.
6. Go to **Trusted Sites** and add `https://www.google.com` to the list.
7. Apply and confirm.
8. Open a new tab — another pop-up will appear. Uncheck the highlighted box, choose **Add** to trust the site, and close the dialog.
9. Search "download chrome" and open the first result.
10. Click **Download Chrome** (refresh the page if the button doesn't show up).
11. When prompted, choose **Save**, then **Run**, to finish the install.

After that, Chrome installs normally and you can leave IE alone for good.
