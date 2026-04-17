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

    const-string v1, "TV Eingang"
    invoke-virtual {v0, v1}, Landroid/app/AlertDialog$Builder;->setTitle(Ljava/lang/CharSequence;)Landroid/app/AlertDialog$Builder;
    move-result-object v0

    const/16 v1, 0xa
    new-array v1, v1, [Ljava/lang/CharSequence;

    const/4 v2, 0x0
    const-string v3, "Kodi"
    aput-object v3, v1, v2

    const/4 v2, 0x1
    const-string v3, "SAT / DVB-S"
    aput-object v3, v1, v2

    const/4 v2, 0x2
    const-string v3, "DVB-T / Antenne"
    aput-object v3, v1, v2

    const/4 v2, 0x3
    const-string v3, "DVB-C / Kabel"
    aput-object v3, v1, v2

    const/4 v2, 0x4
    const-string v3, "ATV / Analog"
    aput-object v3, v1, v2

    const/4 v2, 0x5
    const-string v3, "HDMI 1"
    aput-object v3, v1, v2

    const/4 v2, 0x6
    const-string v3, "HDMI 2"
    aput-object v3, v1, v2

    const/4 v2, 0x7
    const-string v3, "HDMI 3"
    aput-object v3, v1, v2

    const/16 v2, 0x8
    const-string v3, "HDMI 4"
    aput-object v3, v1, v2

    const/16 v2, 0x9
    const-string v3, "Composite / CVBS"
    aput-object v3, v1, v2

    invoke-virtual {v0, v1, p0}, Landroid/app/AlertDialog$Builder;->setItems([Ljava/lang/CharSequence;Landroid/content/DialogInterface$OnClickListener;)Landroid/app/AlertDialog$Builder;
    move-result-object v0

    invoke-virtual {v0, p0}, Landroid/app/AlertDialog$Builder;->setOnCancelListener(Landroid/content/DialogInterface$OnCancelListener;)Landroid/app/AlertDialog$Builder;
    move-result-object v0

    invoke-virtual {v0}, Landroid/app/AlertDialog$Builder;->show()Landroid/app/AlertDialog;
    return-void
.end method

.method public onClick(Landroid/content/DialogInterface;I)V
    .locals 1

    if-nez p2, :not0
    invoke-direct {p0}, Lde/gerontec/kodilauncher/LauncherActivity;->startKodi()V
    goto :done

    :not0
    const/4 v0, 0x1
    if-ne p2, v0, :not1
    const/4 v0, 0x2
    invoke-direct {p0, v0}, Lde/gerontec/kodilauncher/LauncherActivity;->startTuner(I)V
    goto :done

    :not1
    const/4 v0, 0x2
    if-ne p2, v0, :not2
    const/4 v0, 0x0
    invoke-direct {p0, v0}, Lde/gerontec/kodilauncher/LauncherActivity;->startTuner(I)V
    goto :done

    :not2
    const/4 v0, 0x3
    if-ne p2, v0, :not3
    const/4 v0, 0x1
    invoke-direct {p0, v0}, Lde/gerontec/kodilauncher/LauncherActivity;->startTuner(I)V
    goto :done

    :not3
    const/4 v0, 0x4
    if-ne p2, v0, :not4
    const/4 v0, -0x1
    invoke-direct {p0, v0}, Lde/gerontec/kodilauncher/LauncherActivity;->startTuner(I)V
    goto :done

    :not4
    const/4 v0, 0x5
    if-ne p2, v0, :not5
    const-string v0, "com.mediatek.tis/.HdmiInputService/HW2"
    invoke-direct {p0, v0}, Lde/gerontec/kodilauncher/LauncherActivity;->startHdmi(Ljava/lang/String;)V
    goto :done

    :not5
    const/4 v0, 0x6
    if-ne p2, v0, :not6
    const-string v0, "com.mediatek.tis/.HdmiInputService/HW3"
    invoke-direct {p0, v0}, Lde/gerontec/kodilauncher/LauncherActivity;->startHdmi(Ljava/lang/String;)V
    goto :done

    :not6
    const/4 v0, 0x7
    if-ne p2, v0, :not7
    const-string v0, "com.mediatek.tis/.HdmiInputService/HW4"
    invoke-direct {p0, v0}, Lde/gerontec/kodilauncher/LauncherActivity;->startHdmi(Ljava/lang/String;)V
    goto :done

    :not7
    const/16 v0, 0x8
    if-ne p2, v0, :not8
    const-string v0, "com.mediatek.tis/.HdmiInputService/HW5"
    invoke-direct {p0, v0}, Lde/gerontec/kodilauncher/LauncherActivity;->startHdmi(Ljava/lang/String;)V
    goto :done

    :not8
    const/16 v0, 0x9
    if-ne p2, v0, :done
    const-string v0, "com.mediatek.tis/.CompositeInputService/HW6"
    invoke-direct {p0, v0}, Lde/gerontec/kodilauncher/LauncherActivity;->startHdmi(Ljava/lang/String;)V

    :done
    invoke-virtual {p0}, Lde/gerontec/kodilauncher/LauncherActivity;->finish()V
    return-void
.end method

.method public onCancel(Landroid/content/DialogInterface;)V
    .locals 0
    invoke-virtual {p0}, Lde/gerontec/kodilauncher/LauncherActivity;->finish()V
    return-void
.end method

.method private startKodi()V
    .locals 4
    :try_s
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
    :try_e
    .catch Ljava/lang/Exception; {:try_s .. :try_e} :catch_e
    :catch_e
    return-void
.end method

.method private startTuner(I)V
    .locals 4
    :try_s
    new-instance v0, Landroid/content/Intent;
    const-string v1, "com.mediatek.tv.action.TUNER_TYPE"
    invoke-direct {v0, v1}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V
    new-instance v1, Landroid/content/ComponentName;
    const-string v2, "com.mediatek.tv.oneworld.tvcenter"
    const-string v3, "com.mediatek.tv.oneworld.tvcenter.nav.TurnkeyUiMainActivity"
    invoke-direct {v1, v2, v3}, Landroid/content/ComponentName;-><init>(Ljava/lang/String;Ljava/lang/String;)V
    invoke-virtual {v0, v1}, Landroid/content/Intent;->setComponent(Landroid/content/ComponentName;)Landroid/content/Intent;
    const-string v1, "tunerType"
    invoke-virtual {v0, v1, p1}, Landroid/content/Intent;->putExtra(Ljava/lang/String;I)Landroid/content/Intent;
    const/high16 v1, 0x10000000
    invoke-virtual {v0, v1}, Landroid/content/Intent;->addFlags(I)Landroid/content/Intent;
    invoke-virtual {p0, v0}, Lde/gerontec/kodilauncher/LauncherActivity;->startActivity(Landroid/content/Intent;)V
    :try_e
    .catch Ljava/lang/Exception; {:try_s .. :try_e} :catch_e
    :catch_e
    return-void
.end method

.method private startHdmi(Ljava/lang/String;)V
    .locals 4
    :try_s
    new-instance v0, Landroid/content/Intent;
    const-string v1, "android.intent.action.VIEW"
    const-string v2, "content://android.media.tv/channel"
    invoke-static {v2}, Landroid/net/Uri;->parse(Ljava/lang/String;)Landroid/net/Uri;
    move-result-object v2
    invoke-direct {v0, v1, v2}, Landroid/content/Intent;-><init>(Ljava/lang/String;Landroid/net/Uri;)V
    new-instance v1, Landroid/content/ComponentName;
    const-string v2, "com.mediatek.tv.oneworld.tvcenter"
    const-string v3, "com.mediatek.tv.oneworld.tvcenter.nav.TurnkeyUiMainActivity"
    invoke-direct {v1, v2, v3}, Landroid/content/ComponentName;-><init>(Ljava/lang/String;Ljava/lang/String;)V
    invoke-virtual {v0, v1}, Landroid/content/Intent;->setComponent(Landroid/content/ComponentName;)Landroid/content/Intent;
    const-string v1, "android.media.tv.extra.INPUT_ID"
    invoke-virtual {v0, v1, p1}, Landroid/content/Intent;->putExtra(Ljava/lang/String;Ljava/lang/String;)Landroid/content/Intent;
    const/high16 v1, 0x10000000
    invoke-virtual {v0, v1}, Landroid/content/Intent;->addFlags(I)Landroid/content/Intent;
    invoke-virtual {p0, v0}, Lde/gerontec/kodilauncher/LauncherActivity;->startActivity(Landroid/content/Intent;)V
    :try_e
    .catch Ljava/lang/Exception; {:try_s .. :try_e} :catch_e
    :catch_e
    return-void
.end method
