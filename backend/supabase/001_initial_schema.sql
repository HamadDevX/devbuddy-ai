-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Profiles (extends auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
  username TEXT UNIQUE,
  email TEXT UNIQUE,
  tier TEXT DEFAULT 'free' CHECK (tier IN ('free', 'premium')),
  trial_start_date TIMESTAMPTZ DEFAULT NOW(),
  daily_message_count INT DEFAULT 0,
  daily_photo_count INT DEFAULT 0,
  daily_download_count INT DEFAULT 0,
  daily_reset_date DATE DEFAULT CURRENT_DATE,
  theme_preference TEXT DEFAULT 'dark' CHECK (theme_preference IN ('light', 'dark', 'coder')),
  payment_status TEXT DEFAULT 'none',
  transaction_id TEXT,
  premium_expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS policies for profiles
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users own their profile" ON public.profiles
  FOR ALL USING (auth.uid() = id);

CREATE POLICY "Public profiles are readable" ON public.profiles
  FOR SELECT USING (true);

-- Projects table
CREATE TABLE IF NOT EXISTS public.projects (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
  name TEXT NOT NULL,
  tech_stack TEXT,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_projects_user_id ON public.projects(user_id);

CREATE POLICY "Users own their projects" ON public.projects
  FOR ALL USING (auth.uid() = user_id);

-- Chats table
CREATE TABLE IF NOT EXISTS public.chats (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
  project_id UUID REFERENCES public.projects(id) ON DELETE SET NULL,
  role TEXT CHECK (role IN ('user', 'assistant')) NOT NULL,
  content TEXT NOT NULL,
  mode TEXT DEFAULT 'chat',
  explain_mode TEXT,
  humanizer_mode TEXT,
  has_image BOOLEAN DEFAULT FALSE,
  image_urls TEXT[] DEFAULT ARRAY[]::TEXT[],
  code_language TEXT,
  execution_output TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.chats ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_chats_user_id ON public.chats(user_id);
CREATE INDEX idx_chats_project_id ON public.chats(project_id);
CREATE INDEX idx_chats_created_at ON public.chats(created_at DESC);

CREATE POLICY "Users own their chats" ON public.chats
  FOR ALL USING (auth.uid() = user_id);

-- Payments table
CREATE TABLE IF NOT EXISTS public.payments (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
  amount INT NOT NULL,
  currency TEXT DEFAULT 'PKR',
  plan TEXT DEFAULT 'monthly' CHECK (plan IN ('monthly', 'yearly')),
  method TEXT DEFAULT 'meezan',
  transaction_id TEXT UNIQUE,
  screenshot_url TEXT,
  iban_verified BOOLEAN DEFAULT FALSE,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'rejected')),
  admin_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_payments_user_id ON public.payments(user_id);
CREATE INDEX idx_payments_status ON public.payments(status);

CREATE POLICY "Users own their payments" ON public.payments
  FOR ALL USING (auth.uid() = user_id);

-- Storage buckets
INSERT INTO storage.buckets (id, name, public) 
VALUES ('chat-images', 'chat-images', true)
ON CONFLICT DO NOTHING;

INSERT INTO storage.buckets (id, name, public) 
VALUES ('payment-screenshots', 'payment-screenshots', true)
ON CONFLICT DO NOTHING;

-- Storage policies
CREATE POLICY "Users can upload chat images" ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'chat-images' AND 
    auth.uid()::text = (storage.foldername(name))[1]
  );

CREATE POLICY "Users can view their chat images" ON storage.objects
  FOR SELECT USING (
    bucket_id = 'chat-images' AND 
    auth.uid()::text = (storage.foldername(name))[1]
  );

CREATE POLICY "Users can upload payment screenshots" ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'payment-screenshots' AND 
    auth.uid()::text = (storage.foldername(name))[1]
  );

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.profiles
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON public.projects
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_chats_updated_at BEFORE UPDATE ON public.chats
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON public.payments
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Helper function for daily resets
CREATE OR REPLACE FUNCTION public.reset_daily_limits()
RETURNS void AS $$
BEGIN
  UPDATE public.profiles
  SET
    daily_message_count = 0,
    daily_photo_count = 0,
    daily_download_count = 0,
    daily_reset_date = CURRENT_DATE
  WHERE daily_reset_date < CURRENT_DATE;
END;
$$ LANGUAGE plpgsql;