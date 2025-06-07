"use client";

import React, { useEffect, useState, useCallback, FormEvent, ChangeEvent } from "react";
import { useRouter } from "next/navigation"; // Not strictly needed yet, but good for future use
import {
  listSettings,
  upsertSetting,
  deleteSetting,
  getEffectiveSetting, // We might need to call this for a list of known keys
  SettingRead,
  SettingCreate,
  SettingUpdate,
  SettingValue,
} from "../../lib/api";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea"; // For JSON values
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Settings as SettingsIcon, PlusCircle, Edit3, Trash2, Loader2, AlertCircle, Eye } from "lucide-react";

// Assume a way to get current user ID (e.g., from an auth context)
// For now, placeholder. In a real app, replace with actual auth logic.
const useAuth = () => {
    // In a real app, this would come from your auth context/hook
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const storedUser = typeof window !== "undefined" ? localStorage.getItem("user") : null;
    let userId = 1; // Default or guest user ID
    let isAdmin = false; // Default to not admin
    if (storedUser) {
        try {
            const userObj = JSON.parse(storedUser);
            userId = userObj.id || 1;
            isAdmin = userObj.role === 'admin' || userObj.is_superuser === true; // Adjust based on your user object structure
        } catch (e) {
            console.error("Failed to parse user from localStorage", e);
        }
    }
    return { userId, isAdmin, token };
};


type ValueType = 'string' | 'number' | 'boolean' | 'json';

const predefinedEffectiveSettingKeys = ["theme", "notifications_enabled", "max_items_per_page", "feature_flag_xyz"];

export default function SettingsPage() {
  const { userId, isAdmin, token } = useAuth();

  const [effectiveSettings, setEffectiveSettings] = useState<Record<string, SettingValue>>({});
  const [userSettings, setUserSettings] = useState<SettingRead[]>([]);
  const [globalSettings, setGlobalSettings] = useState<SettingRead[]>([]); // For admin view

  const [loadingEffective, setLoadingEffective] = useState(false);
  const [loadingUser, setLoadingUser] = useState(false);
  const [loadingGlobal, setLoadingGlobal] = useState(false); // For admin view

  const [error, setError] = useState<string | null>(null);

  // Form state for creating/editing settings
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingSetting, setEditingSetting] = useState<SettingRead | null>(null);
  const [settingKey, setSettingKey] = useState("");
  const [settingValue, setSettingValue] = useState<string>(""); // Store all as string initially
  const [settingValueType, setSettingValueType] = useState<ValueType>("string");
  const [isGlobalSettingForm, setIsGlobalSettingForm] = useState(false); // For admin form context
  const [formError, setFormError] = useState<string | null>(null);
  const [formLoading, setFormLoading] = useState(false);

  const fetchEffectiveSettings = useCallback(async () => {
    if (!token) return;
    setLoadingEffective(true);
    const newEffectiveSettings: Record<string, SettingValue> = {};
    try {
      for (const key of predefinedEffectiveSettingKeys) {
        const setting = await getEffectiveSetting(key, token); // This API should handle user context via token
        newEffectiveSettings[key] = setting.value;
      }
      setEffectiveSettings(newEffectiveSettings);
    } catch (err: any) {
      setError(err.message || "Failed to fetch effective settings.");
    } finally {
      setLoadingEffective(false);
    }
  }, [token]);

  const fetchUserSettings = useCallback(async () => {
    if (!userId || !token) return;
    setLoadingUser(true);
    try {
      const settings = await listSettings({ user_id: userId }, token);
      setUserSettings(settings);
    } catch (err: any) {
      setError(err.message || "Failed to fetch user settings.");
    } finally {
      setLoadingUser(false);
    }
  }, [userId, token]);

  const fetchGlobalSettings = useCallback(async () => { // For Admin
    if (!isAdmin || !token) return;
    setLoadingGlobal(true);
    try {
      const settings = await listSettings({ /* user_id implicitly null/absent for global */ }, token);
      // Filter for settings that are explicitly global or have no user_id
      // This depends on how your backend defines global settings via listSettings
      setGlobalSettings(settings.filter(s => !s.user_id));
    } catch (err: any) {
      setError(err.message || "Failed to fetch global settings.");
    } finally {
      setLoadingGlobal(false);
    }
  }, [isAdmin, token]);


  useEffect(() => {
    fetchEffectiveSettings();
    fetchUserSettings();
    if (isAdmin) {
      fetchGlobalSettings();
    }
  }, [fetchEffectiveSettings, fetchUserSettings, fetchGlobalSettings, isAdmin]);

  const parseSettingValue = (valueStr: string, type: ValueType): SettingValue => {
    switch (type) {
      case 'number': return parseFloat(valueStr);
      case 'boolean': return valueStr.toLowerCase() === 'true';
      case 'json': try { return JSON.parse(valueStr); } catch (e) { throw new Error("Invalid JSON string"); }
      case 'string':
      default: return valueStr;
    }
  };

  const formatSettingValueForInput = (value: SettingValue, type: ValueType): string => {
    if (value === null || value === undefined) return "";
    if (type === 'json') return JSON.stringify(value, null, 2);
    return String(value);
  };

  const inferValueType = (value: SettingValue): ValueType => {
    const t = typeof value;
    if (t === 'number') return 'number';
    if (t === 'boolean') return 'boolean';
    if (t === 'object') return 'json';
    return 'string';
  };

  const openFormForNew = (isGlobalContext: boolean = false) => {
    setEditingSetting(null);
    setSettingKey("");
    setSettingValue("");
    setSettingValueType("string");
    setIsGlobalSettingForm(isGlobalContext && isAdmin);
    setFormError(null);
    setIsFormOpen(true);
  };

  const openFormForEdit = (setting: SettingRead) => {
    setEditingSetting(setting);
    setSettingKey(setting.key);
    const inferredType = inferValueType(setting.value as SettingValue);
    setSettingValueType(inferredType);
    setSettingValue(formatSettingValueForInput(setting.value as SettingValue, inferredType));
    setIsGlobalSettingForm(!setting.user_id);
    setFormError(null);
    setIsFormOpen(true);
  };

  const handleFormSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!settingKey.trim()) { setFormError("Setting key is required."); return; }

    let parsedValue;
    try {
      parsedValue = parseSettingValue(settingValue, settingValueType);
    } catch (err: any) {
      setFormError(err.message);
      return;
    }

    setFormLoading(true);
    setFormError(null);

    const settingPayload: SettingCreate = {
      key: settingKey,
      value: parsedValue,
    };

    if (isAdmin && isGlobalSettingForm) {
      settingPayload.user_id = null;
    } else {
      settingPayload.user_id = userId;
    }

    try {
      if (!token) throw new Error("Authentication token not found.");
      // Upsert implies create or update. If editing an existing setting, its ID is in `editingSetting.id`.
      // The current `upsertSetting` API takes `key` in path and payload.
      // If `editingSetting` exists, we are essentially updating it by its key.
      await upsertSetting(settingKey, settingPayload, token);

      setIsFormOpen(false);
      fetchUserSettings();
      if (isAdmin) fetchGlobalSettings();
      fetchEffectiveSettings();
    } catch (err: any) {
      setFormError(err.message || "Failed to save setting.");
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteSetting = async (settingId: number, isGlobalContext: boolean) => {
    // Admin check for global settings deletion
    if (isGlobalContext && !isAdmin) {
        setError("Unauthorized to delete global settings.");
        return;
    }
    if (!window.confirm("Are you sure you want to delete this setting?")) return;
    try {
      if (!token) throw new Error("Authentication token not found.");
      await deleteSetting(settingId, token);
      fetchUserSettings();
      if (isAdmin) fetchGlobalSettings();
      fetchEffectiveSettings();
    } catch (err: any) {
      setError(err.message || "Failed to delete setting.");
    }
  };

  const renderValueInput = () => {
    if (settingValueType === 'boolean') {
      return (
        <Select value={settingValue} onValueChange={(val) => setSettingValue(val)}>
          <SelectTrigger className="dark:bg-gray-700 dark:border-gray-600"><SelectValue placeholder="Select boolean value"/></SelectTrigger>
          <SelectContent className="dark:bg-gray-700 dark:text-white">
            <SelectItem value="true">True</SelectItem>
            <SelectItem value="false">False</SelectItem>
          </SelectContent>
        </Select>
      );
    } else if (settingValueType === 'json') {
      return <Textarea value={settingValue} onChange={(e) => setSettingValue(e.target.value)} rows={5} placeholder='Enter JSON value' className="font-mono dark:bg-gray-700 dark:border-gray-600"/>;
    } else {
      return <Input type={settingValueType === 'number' ? 'number' : 'text'} value={settingValue} onChange={(e) => setSettingValue(e.target.value)} placeholder="Enter value" className="dark:bg-gray-700 dark:border-gray-600"/>;
    }
  };

  const renderEffectiveSettings = () => (
    <CardContent>
      {loadingEffective && <div className="flex justify-center p-4"><Loader2 className="animate-spin" /></div>}
      {!loadingEffective && Object.keys(effectiveSettings).length === 0 && <p className="text-sm text-gray-500 dark:text-gray-400">No effective settings loaded or defined for predefined keys.</p>}
      <dl className="space-y-2">
        {Object.entries(effectiveSettings).map(([key, value]) => (
          <div key={key} className="flex justify-between items-center p-2 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700/50">
            <dt className="font-medium dark:text-gray-300">{key}:</dt>
            <dd className="text-gray-700 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-sm text-sm">{String(value)}</dd>
          </div>
        ))}
      </dl>
    </CardContent>
  );

  const renderSettingsTable = (title: string, settings: SettingRead[], isGlobalTable: boolean) => (
    <CardContent>
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xl font-semibold dark:text-white">{title}</h3>
        { (isAdmin || !isGlobalTable) &&
          <Button size="sm" onClick={() => openFormForNew(isGlobalTable)} className="bg-sky-500 hover:bg-sky-600"><PlusCircle className="w-4 h-4 mr-2"/>Add New</Button>
        }
      </div>
      { (isGlobalTable && loadingGlobal || !isGlobalTable && loadingUser) && <div className="flex justify-center p-4"><Loader2 className="animate-spin" /></div>}
      { !loadingUser && !isGlobalTable && settings.length === 0 && <p className="text-sm text-gray-500 dark:text-gray-400">You have no custom settings. Add one above!</p>}
      { !loadingGlobal && isGlobalTable && settings.length === 0 && <p className="text-sm text-gray-500 dark:text-gray-400">No global settings found.</p>}

      {settings.length > 0 && (
        <div className="overflow-x-auto">
        <Table>
          <TableHeader><TableRow><TableHead className="dark:text-gray-300">Key</TableHead><TableHead className="dark:text-gray-300">Value</TableHead><TableHead className="dark:text-gray-300">Type</TableHead><TableHead className="dark:text-gray-300 text-right">Actions</TableHead></TableRow></TableHeader>
          <TableBody>
            {settings.map(s => (
              <TableRow key={s.id} className="dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <TableCell className="font-medium dark:text-gray-300">{s.key}</TableCell>
                <TableCell className="text-sm dark:text-gray-400 truncate max-w-sm">{typeof s.value === 'object' ? JSON.stringify(s.value) : String(s.value)}</TableCell>
                <TableCell><Badge variant="outline" className="dark:border-gray-600 dark:text-gray-300">{inferValueType(s.value as SettingValue)}</Badge></TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="icon" onClick={() => openFormForEdit(s)} className="dark:text-gray-400 hover:dark:text-blue-400"><Edit3 className="w-4 h-4"/></Button>
                  <Button variant="ghost" size="icon" onClick={() => handleDeleteSetting(s.id, isGlobalTable)} className="dark:text-gray-400 hover:dark:text-red-400"><Trash2 className="w-4 h-4"/></Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        </div>
      )}
    </CardContent>
  );

  return (
    <div className="container mx-auto py-8 px-4 md:px-6 lg:px-8">
      <div className="flex items-center mb-8">
        <SettingsIcon className="w-10 h-10 mr-4 text-sky-500" />
        <h1 className="text-4xl font-bold text-gray-800 dark:text-white">Settings</h1>
      </div>

      {error && <Alert variant="destructive" className="mb-6"><AlertCircle className="h-4 w-4"/><AlertTitle>Page Error</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}

      <Tabs defaultValue="effective" className="w-full">
        <TabsList className="grid w-full grid-cols-2 md:grid-cols-3 mb-6 dark:bg-gray-900 border dark:border-gray-700">
          <TabsTrigger value="effective" className="dark:data-[state=active]:bg-sky-600 dark:data-[state=active]:text-white dark:text-gray-300">Effective</TabsTrigger>
          <TabsTrigger value="user" className="dark:data-[state=active]:bg-sky-600 dark:data-[state=active]:text-white dark:text-gray-300">My Settings</TabsTrigger>
          {isAdmin && <TabsTrigger value="global" className="dark:data-[state=active]:bg-sky-600 dark:data-[state=active]:text-white dark:text-gray-300">Global (Admin)</TabsTrigger>}
        </TabsList>

        <TabsContent value="effective">
          <Card className="dark:bg-gray-800 shadow-md"><CardHeader><CardTitle className="dark:text-white flex items-center"><Eye className="w-5 h-5 mr-2 text-sky-400"/>Effective Settings</CardTitle><CardDescription className="dark:text-gray-400">Final values applied, combining global and your custom settings for predefined keys.</CardDescription></CardHeader>{renderEffectiveSettings()}</Card>
        </TabsContent>

        <TabsContent value="user">
          <Card className="dark:bg-gray-800 shadow-md">{renderSettingsTable("My Custom Settings", userSettings, false)}</Card>
        </TabsContent>

        {isAdmin && (
          <TabsContent value="global">
            <Card className="dark:bg-gray-800 shadow-md">{renderSettingsTable("Global Settings", globalSettings, true)}</Card>
          </TabsContent>
        )}
      </Tabs>

      {isFormOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 flex justify-center items-center p-4" onClick={() => setIsFormOpen(false)}>
        <Card className="w-full max-w-lg dark:bg-gray-800 border-sky-500 border z-50" onClick={(e) => e.stopPropagation()}>
          <CardHeader>
            <CardTitle className="dark:text-white">{editingSetting ? "Edit Setting" : (isAdmin && isGlobalSettingForm ? "Create Global Setting" : "Create My Setting")}</CardTitle>
            {formError && <Alert variant="destructive" className="mt-2"><AlertCircle className="h-4 w-4"/><AlertDescription>{formError}</AlertDescription></Alert>}
          </CardHeader>
          <CardContent>
            <form onSubmit={handleFormSubmit} className="space-y-4">
              <div>
                <Label htmlFor="settingKey" className="dark:text-gray-300">Key <span className="text-red-500">*</span></Label>
                <Input id="settingKey" value={settingKey} onChange={(e) => setSettingKey(e.target.value)} placeholder="setting.key.name" required disabled={!!editingSetting} className="dark:bg-gray-700 dark:border-gray-600"/>
                {editingSetting && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Key cannot be changed for existing settings.</p>}
              </div>
              <div>
                <Label htmlFor="settingValueType" className="dark:text-gray-300">Value Type</Label>
                <Select value={settingValueType} onValueChange={(v) => {setSettingValueType(v as ValueType); if(v === 'boolean' && settingValue === "") setSettingValue("false");} }>
                  <SelectTrigger className="dark:bg-gray-700 dark:border-gray-600"><SelectValue /></SelectTrigger>
                  <SelectContent className="dark:bg-gray-700 dark:text-white">
                    <SelectItem value="string">String</SelectItem><SelectItem value="number">Number</SelectItem>
                    <SelectItem value="boolean">Boolean</SelectItem><SelectItem value="json">JSON</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="settingValue" className="dark:text-gray-300">Value <span className="text-red-500">*</span></Label>
                {renderValueInput()}
              </div>
              {isAdmin && !editingSetting && (
                <div className="flex items-center space-x-2">
                    <Checkbox id="isGlobalSettingForm" checked={isGlobalSettingForm} onCheckedChange={(checked) => setIsGlobalSettingForm(Boolean(checked))} className="dark:border-gray-600 data-[state=checked]:bg-sky-500"/>
                    <Label htmlFor="isGlobalSettingForm" className="dark:text-gray-300">Set as Global Setting</Label>
                </div>
              )}
              <div className="flex justify-end space-x-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setIsFormOpen(false)} className="dark:text-gray-300 dark:border-gray-600" disabled={formLoading}>Cancel</Button>
                <Button type="submit" className="bg-sky-500 hover:bg-sky-600 text-white" disabled={formLoading}>
                  {formLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {editingSetting ? "Save Changes" : "Create Setting"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
        </div>
      )}
    </div>
  );
}
