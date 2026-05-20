"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Plus, LogIn, LogOut } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import { createRoomSchema, CreateRoomFormData, joinRoomSchema, JoinRoomFormData } from "@/lib/validators";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";

export default function DashboardPage() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  const [isCreating, setIsCreating] = useState(false);
  const [isJoining, setIsJoining] = useState(false);

  useEffect(() => {
    if (!user) {
      router.push("/login");
    }
  }, [user]);

  const createForm = useForm<CreateRoomFormData>({
    resolver: zodResolver(createRoomSchema),
    defaultValues: { title: "", challenge_prompt: "" },
  });

  const joinForm = useForm<JoinRoomFormData>({
    resolver: zodResolver(joinRoomSchema),
    defaultValues: { code: "" },
  });

  async function onCreateSubmit(data: CreateRoomFormData) {
    setIsCreating(true);
    try {
      const res = await api.post("/rooms", data);
      toast.success("Room created!");
      router.push(`/rooms/${res.data.code}`);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to create room");
    } finally {
      setIsCreating(false);
    }
  }

  async function onJoinSubmit(data: JoinRoomFormData) {
    setIsJoining(true);
    try {
      // First try to get the room to make sure it exists
      await api.get(`/rooms/${data.code}`);
      
      // Then join it
      await api.post(`/rooms/${data.code}/join`);
      toast.success("Joined room!");
      router.push(`/rooms/${data.code}`);
    } catch (error: any) {
      if (error.response?.status === 409) {
        // Already joined
        router.push(`/rooms/${data.code}`);
      } else {
        toast.error(error.response?.data?.detail || "Failed to join room");
      }
    } finally {
      setIsJoining(false);
    }
  }

  function handleLogout() {
    logout();
    document.cookie = "poiro_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT";
    router.push("/login");
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-950">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50 p-6">
      <div className="max-w-4xl mx-auto space-y-8">
        <header className="flex justify-between items-center py-4">
          <h1 className="text-3xl font-bold tracking-tight text-sans">Poiro</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm">Welcome, {user?.display_name}</span>
            <Button variant="outline" size={"sm"} onClick={handleLogout} className="text-xs">
              <LogOut className="h-4 w-4" />
              Sign Out
            </Button>
          </div>
        </header>

        <div className="grid md:grid-cols-2 gap-8">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plus className="h-5 w-5" />
                Create a Battle Room
              </CardTitle>
              <CardDescription className="text-zinc-400">
                Host a new creative challenge and invite participants.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...createForm}>
                <form onSubmit={createForm.handleSubmit(onCreateSubmit)} className="space-y-4">
                  <FormField
                    control={createForm.control}
                    name="title"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Room Title</FormLabel>
                        <FormControl>
                          <Input placeholder="Cyberpunk Haiku Battle" className="bg-zinc-950 border-zinc-800" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={createForm.control}
                    name="challenge_prompt"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Challenge Description (Context)</FormLabel>
                        <FormControl>
                          <Input 
                            placeholder="Write a 3-line haiku about a rogue AI..." 
                            className="bg-zinc-950 border-zinc-800"
                            {...field} 
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button type="submit" className="w-full" disabled={isCreating}>
                    {isCreating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : "Create Room"}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>

          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LogIn className="h-5 w-5" />
                Join a Battle Room
              </CardTitle>
              <CardDescription className="text-zinc-400">
                Enter a 6-character invite code to join an existing room.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...joinForm}>
                <form onSubmit={joinForm.handleSubmit(onJoinSubmit)} className="space-y-4">
                  <FormField
                    control={joinForm.control}
                    name="code"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Join Code</FormLabel>
                        <FormControl>
                          <Input 
                            placeholder="ABC123" 
                            className="bg-zinc-950 border-zinc-800 uppercase"
                            maxLength={6}
                            {...field} 
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <Button type="submit" className="w-full" disabled={isJoining}>
                    {isJoining ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : "Join Room"}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
