-- ==============================================================================
-- OPTIONAL: FULL DATABASE RESET FOR LOCAL / TESTING RE-RUNS
-- ==============================================================================
-- Uncomment the four lines below if you want to completely wipe and rebuild
-- the public schema when running this script:
drop schema if exists public cascade;

create schema public;

grant all on schema public to postgres;

grant all on schema public to public;

-- ==============================================================================
-- PyToNingans Community Mod Browser - Supabase Database Schema
-- ==============================================================================
-- MODS TABLE
create table if not exists public.mods (
  id text primary key,
  name text not null,
  entity_type text not null,
  version text not null default '1.0.0',
  author text not null,
  author_id uuid references auth.users (id) on delete set null,
  description text not null default '',
  tags text[] not null default '{}',
  is_pack boolean not null default false,
  contained_entities text[] not null default '{}',
  config_version integer not null default 10,
  target_app_version text not null default '0.8.3',
  package_url text,
  icon_url text,
  downloads integer not null default 0,
  size_bytes bigint not null default 0,
  verification_status text not null default 'pending' check (
    verification_status in ('pending', 'approved', 'rejected')
  ),
  verified_by uuid references auth.users (id) on delete set null,
  verified_at timestamp with time zone,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now()
);

-- Foreign Key & Filter Indexes
create index if not exists idx_mods_author_id on public.mods (author_id);

create index if not exists idx_mods_verification_status on public.mods (verification_status);

create index if not exists idx_mods_verified_by on public.mods (verified_by);

-- MOD RELEASES TABLE
create table if not exists public.mod_releases (
  id uuid primary key default gen_random_uuid(),
  mod_id text not null references public.mods (id) on delete cascade,
  version text not null,
  changelog text not null default '',
  download_url text,
  size_bytes bigint not null default 0,
  config_version integer not null default 10,
  target_app_version text not null default '0.8.3',
  created_at timestamp with time zone not null default now(),
  unique (mod_id, version)
);

-- MOD RATINGS TABLE
create table if not exists public.mod_ratings (
  mod_id text not null references public.mods (id) on delete cascade,
  user_id uuid not null references auth.users (id) on delete cascade,
  rating numeric(3, 1) not null check (
    rating >= 1.0
    and rating <= 10.0
  ),
  created_at timestamp with time zone not null default now(),
  primary key (mod_id, user_id)
);

create index if not exists idx_mod_ratings_user_id on public.mod_ratings (user_id);

-- CREATOR ROLES TABLE
create table if not exists public.creator_roles (
  user_id uuid primary key references auth.users (id) on delete cascade,
  role text not null default 'developer',
  handle text,
  github_username text,
  email text,
  description text default '',
  created_at timestamp with time zone not null default now()
);

-- ADMINS TABLE
create table if not exists public.admins (
  user_id uuid primary key references auth.users (id) on delete cascade,
  granted_by uuid references auth.users (id) on delete set null,
  granted_at timestamp with time zone not null default now(),
  note text default '',
  created_at timestamp with time zone not null default now()
);

create index if not exists idx_admins_granted_by on public.admins (granted_by);

-- ==============================================================================
-- AUTOMATIC UPDATED_AT TRIGGER (WITH SEARCH_PATH FIX)
-- ==============================================================================
create or replace function public.handle_updated_at () returns trigger language plpgsql
set
  search_path = '' as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_mods_updated_at on public.mods;

create trigger set_mods_updated_at
before update on public.mods for each row
execute function public.handle_updated_at ();

-- ==============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ==============================================================================
alter table public.mods enable row level security;

alter table public.mod_releases enable row level security;

alter table public.mod_ratings enable row level security;

alter table public.creator_roles enable row level security;

alter table public.admins enable row level security;

-- --- Creator Roles Policies ---
drop policy if exists "Creator roles are viewable by everyone" on public.creator_roles;

create policy "Creator roles are viewable by everyone" on public.creator_roles for
select
  using (true);

-- --- Admins Table Policies ---
drop policy if exists "Admins are viewable by authenticated users" on public.admins;

create policy "Admins are viewable by authenticated users" on public.admins for
select
  using (
    (
      select
        auth.role ()
    ) = 'authenticated'
  );

-- Seed Core Developer Account (using metadata mapping)
insert into
  public.creator_roles (
    user_id,
    role,
    handle,
    github_username,
    email,
    description
  )
select
  id as user_id,
  'developer' as role,
  'Meta-Dusk' as handle,
  'Meta-Dusk' as github_username,
  email,
  'Core Developer & Author' as description
from
  auth.users
where
  raw_user_meta_data ->> 'user_name' = 'Meta-Dusk'
on conflict (user_id) do update
set role = excluded.role,
handle = excluded.handle,
github_username = excluded.github_username;

-- --- Mods Policies ---
drop policy if exists "Mods are viewable by everyone" on public.mods;

create policy "Mods are viewable by everyone" on public.mods for
select
  using (true);

drop policy if exists "Authenticated creators can publish mods" on public.mods;

create policy "Authenticated creators can publish mods" on public.mods for insert
with
  check (
    (
      select
        auth.role ()
    ) = 'authenticated'
  );

drop policy if exists "Creators and admins can update mods" on public.mods;

create policy "Creators and admins can update mods" on public.mods
for update
  using (
    (
      select
        auth.uid ()
    ) = author_id
    or exists (
      select
        1
      from
        public.admins
      where
        user_id = auth.uid ()
    )
  );

drop policy if exists "Creators can delete their own mods" on public.mods;

create policy "Creators can delete their own mods" on public.mods for delete using (
  (
    select
      auth.uid ()
  ) = author_id
);

-- --- Releases Policies ---
drop policy if exists "Releases are viewable by everyone" on public.mod_releases;

create policy "Releases are viewable by everyone" on public.mod_releases for
select
  using (true);

drop policy if exists "Creators can add releases for their mods" on public.mod_releases;

create policy "Creators can add releases for their mods" on public.mod_releases for insert
with
  check (
    exists (
      select
        1
      from
        public.mods
      where
        id = mod_releases.mod_id
        and (
          author_id = (
            select
              auth.uid ()
          )
          or author_id is null
        )
    )
  );

drop policy if exists "Creators can delete releases of their own mods" on public.mod_releases;

create policy "Creators can delete releases of their own mods" on public.mod_releases for delete using (
  exists (
    select
      1
    from
      public.mods
    where
      id = mod_releases.mod_id
      and author_id = (
        select
          auth.uid ()
      )
  )
);

-- --- Ratings Policies ---
drop policy if exists "Ratings are viewable by everyone" on public.mod_ratings;

create policy "Ratings are viewable by everyone" on public.mod_ratings for
select
  using (true);

drop policy if exists "Authenticated users can submit ratings" on public.mod_ratings;

create policy "Authenticated users can submit ratings" on public.mod_ratings for insert
with
  check (
    (
      select
        auth.uid ()
    ) = user_id
  );

drop policy if exists "Authenticated users can update their ratings" on public.mod_ratings;

create policy "Authenticated users can update their ratings" on public.mod_ratings
for update
  using (
    (
      select
        auth.uid ()
    ) = user_id
  )
with
  check (
    (
      select
        auth.uid ()
    ) = user_id
  );

drop policy if exists "Authenticated users can delete their ratings" on public.mod_ratings;

create policy "Authenticated users can delete their ratings" on public.mod_ratings for delete using (
  (
    select
      auth.uid ()
  ) = user_id
);

-- ==============================================================================
-- STORAGE BUCKET FOR MOD PACKAGES (HARDENED FOR PUBLIC CDN USE)
-- ==============================================================================
insert into
  storage.buckets (id, name, public)
values
  ('mods', 'mods', true)
on conflict (id) do nothing;

-- Remove broad object listing policy (prevents public.bucket_allows_listing warning)
drop policy if exists "Authenticated users can select mod packages" on storage.objects;

drop policy if exists "Mod packages are publicly downloadable" on storage.objects;

-- Restrict write/update/delete operations to authenticated users
drop policy if exists "Authenticated creators can upload mod packages" on storage.objects;

create policy "Authenticated creators can upload mod packages" on storage.objects for insert
with
  check (
    bucket_id = 'mods'
    and (
      select
        auth.role ()
    ) = 'authenticated'
  );

drop policy if exists "Creators can update mod packages" on storage.objects;

create policy "Creators can update mod packages" on storage.objects
for update
  using (
    bucket_id = 'mods'
    and (
      select
        auth.role ()
    ) = 'authenticated'
  );

drop policy if exists "Creators can delete mod packages" on storage.objects;

create policy "Creators can delete mod packages" on storage.objects for delete using (
  bucket_id = 'mods'
  and (
    select
      auth.role ()
  ) = 'authenticated'
);

-- ==============================================================================
-- EXPLICIT API GRANTS
-- ==============================================================================
grant usage on schema public to anon,
authenticated;

grant
select
,
  insert,
update,
delete on table public.mods to anon,
authenticated;

grant
select
,
  insert,
update,
delete on table public.mod_releases to anon,
authenticated;

grant
select
,
  insert,
update,
delete on table public.mod_ratings to anon,
authenticated;

grant
select
  on table public.creator_roles to anon,
  authenticated;

grant
select
  on table public.admins to authenticated;

grant usage,
select
  on all sequences in schema public to anon,
  authenticated;

-- ==============================================================================
-- SECURITY HARDENING
-- ==============================================================================
do $$
begin
    if exists (
        select 1 from pg_proc 
        join pg_namespace on pg_proc.pronamespace = pg_namespace.oid 
        where pg_namespace.nspname = 'public' and pg_proc.proname = 'rls_auto_enable'
    ) then
        revoke execute on function public.rls_auto_enable() from public, anon, authenticated;
    end if;
end $$;