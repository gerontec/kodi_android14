.class public Lde/gerontec/kodilauncher/LauncherActivity;
.super Landroid/app/Activity;
.implements Landroid/content/DialogInterface$OnClickListener;
.implements Landroid/content/DialogInterface$OnCancelListener;
.source "LauncherActivity.java"

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Landroid/app/Activity;-><init>()V
    return-void
.end method

.method protected onCreate(Landroid/os/Bundle;)V
    .locals 4

    invoke-super {p0, p1}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V

    new-instance v0, Landroid/app/AlertDialog$Builder;
    invoke-direct {v0, p0}, Landroid/app/AlertDialog$Builder;-><init>(Landroid/content/Context;)V

    const-string v1, "TV Quelle"
    invoke-virtual {v0, v1}, Landroid/app/AlertDialog$Builder;->setTitle(Ljava/lang/CharSequence;)Landroid/app/AlertDialog$Builder;
    move-result-object v0

    const/4 v1, 0x2
    new-array v1, v1, [Ljava/lang/CharSequence;
    const/4 v2, 0x0
    const-string v3, "Kodi"
    aput-object v3, v1, v2
    const/4 v2, 0x1
    const-string v3, "SAT / DVB-S"
    aput-object v3, v1, v2

    invoke-virtual {v0, v1, p0}, Landroid/app/AlertDialog$Builder;->setItems([Ljava/lang/CharSequence;Landroid/content/DialogInterface$OnClickListener;)Landroid/app/AlertDialog$Builder;
    move-result-object v0

    invoke-virtual {v0, p0}, Landroid/app/AlertDialog$Builder;->setOnCancelListener(Landroid/content/DialogInterface$OnCancelListener;)Landroid/app/AlertDialog$Builder;
    move-result-object v0

    invoke-virtual {v0}, Landroid/app/AlertDialog$Builder;->show()Landroid/app/AlertDialog;

    return-void
.end method

.method public onClick(Landroid/content/DialogInterface;I)V
    .locals 4

    if-nez p2, :start_sat

    :try_kodi_s
    new-instance v0, Landroid/content/Intent;
    invoke-direct {v0}, Landroid/content/Intent;-><init>()V
    new-instance v1, Landroid/content/ComponentName;
    const-string v2, "org.xbmc.kodi"
    const-string v3, "org.xbmc.kodi.Splash"
    invoke-direct {v1, v2, v3}, Landroid/content/ComponentName;-><init>(Ljava/lang/String;Ljava/lang/String;)V
    invoke-virtual {v0, v1}, Landroid/content/Intent;->setComponent(Landroid/content/ComponentName;)Landroid/content/Intent;
    const/high16 v1, 0x10000000
    invoke-virtual {v0, v1}, Landroid/content/Intent;->addFlags(I)Landroid/content/Intent;
    invoke-virtual {p0, v0}, Lde/gerontec/kodilauncher/LauncherActivity;->startActivity(Landroid/content/Intent;)V
    :try_kodi_e
    .catch Ljava/lang/Exception; {:try_kodi_s .. :try_kodi_e} :catch_kodi
    goto :finish

    :catch_kodi
    goto :finish

    :start_sat
    :try_sat_s
    new-instance v0, Landroid/content/Intent;
    const-string v1, "com.mediatek.tv.action.TUNER_TYPE"
    invoke-direct {v0, v1}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V
    new-instance v1, Landroid/content/ComponentName;
    const-string v2, "com.mediatek.tv.oneworld.tvcenter"
    const-string v3, "com.mediatek.tv.oneworld.tvcenter.nav.TurnkeyUiMainActivity"
    invoke-direct {v1, v2, v3}, Landroid/content/ComponentName;-><init>(Ljava/lang/String;Ljava/lang/String;)V
    invoke-virtual {v0, v1}, Landroid/content/Intent;->setComponent(Landroid/content/ComponentName;)Landroid/content/Intent;
    const/4 v1, 0x2
    const-string v2, "tunerType"
    invoke-virtual {v0, v2, v1}, Landroid/content/Intent;->putExtra(Ljava/lang/String;I)Landroid/content/Intent;
    const/high16 v1, 0x10000000
    invoke-virtual {v0, v1}, Landroid/content/Intent;->addFlags(I)Landroid/content/Intent;
    invoke-virtual {p0, v0}, Lde/gerontec/kodilauncher/LauncherActivity;->startActivity(Landroid/content/Intent;)V
    :try_sat_e
    .catch Ljava/lang/Exception; {:try_sat_s .. :try_sat_e} :catch_sat
    goto :finish

    :catch_sat

    :finish
    invoke-virtual {p0}, Lde/gerontec/kodilauncher/LauncherActivity;->finish()V
    return-void
.end method

.method public onCancel(Landroid/content/DialogInterface;)V
    .locals 0
    invoke-virtual {p0}, Lde/gerontec/kodilauncher/LauncherActivity;->finish()V
    return-void
.end method
