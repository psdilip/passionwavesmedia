---
title: Getting Chrome onto Windows Server 2019
slug: download-chrome-ie-windows-server-2019
category: How-To
tags: Windows Server, Internet Explorer, Chrome
excerpt: A fresh Windows Server 2019 box only comes with Internet Explorer, here's how to get Chrome onto it without a fight.
date: 2022-02-17
---

![Photo by Lukas on Unsplash](assets/images/download-chrome-ie-windows-server-2019/hero.jpg)
*Photo by [Lukas](https://unsplash.com/@lukash) on [Unsplash](https://unsplash.com)*

A new Windows Server 2019 instance only ships with Internet Explorer, and IE's default security settings actively get in the way of downloading anything, including the browser you'd rather be using. Here's the sequence that gets Chrome installed without fighting it the whole way.

1. When IE opens for the first time, dismiss the initial pop-up with **OK**.
2. Open **Internet Options** from the settings menu.
3. Go to the **Security** tab.
4. Click **Custom Level**, find the **Downloads** section, and enable **File Download**.
5. Click **OK** and confirm the security-settings change when it asks.
6. Go to **Trusted Sites** and add `https://www.google.com` to the list.
7. Apply and confirm.
8. Open a new tab. Another pop-up will appear. Uncheck the highlighted box, choose **Add** to trust the site, and close the dialog.
9. Search "download chrome" and open the first result.
10. Click **Download Chrome** (refresh the page if the button doesn't show up).
11. When prompted, choose **Save**, then **Run**, to finish the install.

After that, Chrome installs normally and you can leave IE alone for good.

## Practical guide: the checklist version

A condensed run-through of the exact steps, in order, for the next time you're stuck on a fresh box with only IE.

1. **Dismiss the first-run pop-up.** Click **OK** when IE opens for the first time so it stops blocking everything else.
2. **Open Internet Options and go to Security.** This is where the download-blocking settings live.
3. **Enable File Download under Custom Level.** Find the **Downloads** section and turn on **File Download**, then click **OK** and confirm the change.
4. **Add google.com to Trusted Sites.** Go to **Trusted Sites**, add `https://www.google.com`, then apply and confirm.
5. **Trust the new tab pop-up too.** Open a new tab, uncheck the highlighted box in the pop-up that appears, choose **Add**, and close the dialog.
6. **Search for Chrome and open the first result.** Search "download chrome" and click through to the official page.
7. **Click Download Chrome.** Refresh the page first if the button doesn't render.
8. **Save, then Run, to finish the install.** Choose **Save** when prompted, then **Run** the installer.
9. **Leave IE alone for good.** Once Chrome installs, there's no reason to go back.
