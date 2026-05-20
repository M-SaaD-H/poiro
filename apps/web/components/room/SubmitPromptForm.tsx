import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Send } from "lucide-react";
import { submitPromptSchema, SubmitPromptFormData } from "@/lib/validators";
import { api } from "@/lib/api";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Form, FormControl, FormField, FormItem, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";

export function SubmitPromptForm({ roundId, hasSubmitted, disabled }: { roundId: string, hasSubmitted: boolean, disabled: boolean }) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const form = useForm<SubmitPromptFormData>({
    resolver: zodResolver(submitPromptSchema),
    defaultValues: { prompt: "" },
  });

  async function onSubmit(data: SubmitPromptFormData) {
    setIsSubmitting(true);
    try {
      await api.post(`/rounds/${roundId}/submissions`, data);
      toast.success("Submission sent!");
      form.reset();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to submit");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (hasSubmitted) {
    return (
      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="py-6 flex flex-col items-center justify-center text-zinc-400">
          <p className="text-center">You have submitted your prompt for this round.</p>
          <p className="text-sm text-zinc-500 mt-1">Waiting for other participants...</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-zinc-900 border-zinc-800 shadow-xl ring-1 ring-white/10">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg text-zinc-100">Submit Your Prompt</CardTitle>
        <CardDescription className="text-zinc-400">Craft your best creative prompt based on the host's challenge.</CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex gap-2">
            <FormField
              control={form.control}
              name="prompt"
              render={({ field }) => (
                <FormItem className="flex-1">
                  <FormControl>
                    <Input 
                      placeholder="Enter your prompt here..." 
                      className="bg-zinc-950 border-zinc-700 text-zinc-100 focus-visible:ring-indigo-500"
                      disabled={disabled || isSubmitting}
                      {...field} 
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button 
              type="submit" 
              className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-900/20"
              disabled={disabled || isSubmitting}
            >
              {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
              {isSubmitting ? "" : "Submit"}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
