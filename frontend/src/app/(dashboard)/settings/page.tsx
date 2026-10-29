"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { getMe, updateMe } from "@/lib/api-client/client";
import type { MeRecord } from "@/lib/api-client/types";

export default function SettingsPage() {
  const [me, setMe] = useState<MeRecord | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [citeFirst, setCiteFirst] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void getMe()
      .then((row) => {
        setMe(row);
        setDisplayName(row.display_name || "");
        setCiteFirst(row.preferences?.cite_first !== false);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load profile"));
  }, []);

  async function handleSave() {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const next = await updateMe({
        display_name: displayName,
        preferences: {
          ...(me?.preferences || {}),
          cite_first: citeFirst,
        },
      });
      setMe(next);
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg space-y-8">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Profile details synced from Neon Auth. Password and account security are managed by
          your identity provider—not stored in this app.
        </p>
      </div>

      {!me && !error ? <p className="text-sm text-zinc-500">Loading profile…</p> : null}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      {me ? (
        <div className="space-y-6 rounded-xl border bg-white p-5">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" value={me.email || ""} disabled readOnly />
          </div>
          <div className="space-y-2">
            <Label htmlFor="display_name">Display name</Label>
            <Input
              id="display_name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </div>
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium">Prefer citations after answers</p>
              <p className="text-xs text-zinc-500">UI preference stored in your profile.</p>
            </div>
            <Switch checked={citeFirst} onCheckedChange={setCiteFirst} />
          </div>
          <p className="text-xs text-zinc-400">
            Corpus version {me.corpus_version} · User id {me.id.slice(0, 8)}…
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" onClick={() => void handleSave()} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
            {saved ? <span className="text-sm text-zinc-500">Saved</span> : null}
          </div>
        </div>
      ) : null}

      <div className="rounded-xl border border-dashed bg-zinc-50 p-5 text-sm text-zinc-600">
        <p className="font-medium text-zinc-900">Account security</p>
        <p className="mt-1">
          Use Neon Auth sign-in flows to change your password or manage sessions. This app does
          not recreate authentication tables or store credentials.
        </p>
      </div>
    </div>
  );
}
