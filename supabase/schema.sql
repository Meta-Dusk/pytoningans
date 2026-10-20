-- ==============================================================================
-- PyToNingans Community Mod Browser - Supabase Database Schema and Storage
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
  target_app_version text not null default '0.8.0',
  package_url text,
  icon_url text,
  downloads integer not null default 0,
  size_bytes bigint not null default 0,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now()
);

-- Foreign key covering index (Performance Advisor: unindexed_foreign_keys)
create index if not exists idx_mods_author_id on public.mods (author_id);

-- MOD RELEASES TABLE (Git-like version history)
create table if not exists public.mod_releases (
  id uuid primary key default gen_random_uuid(),
  mod_id text not null references public.mods (id) on delete cascade,
  version text not null,
  changelog text not null default '',
  download_url text,
  size_bytes bigint not null default 0,
  config_version integer not null default 10,
  target_app_version text not null default '0.8.0',
  created_at timestamp with time zone not null default now(),
  unique (mod_id, version)
);

-- Note: 'unique (mod_id, version)' automatically indexes mod_id as the leading column,
-- so an extra index on mod_id alone is not needed.
-- MOD RATINGS TABLE (1.0 to 10.0 per user per mod)
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

-- Foreign key covering index (Performance Advisor: unindexed_foreign_keys)
create index if not exists idx_mod_ratings_user_id on public.mod_ratings (user_id);

-- CREATOR ROLES TABLE (Flexible role & developer assignment)
create table if not exists public.creator_roles (
  handle text primary key,
  role text not null default 'developer',
  email text,
  description text default '',
  created_at timestamp with time zone not null default now()
);

-- ==============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- Note: Subqueries (select auth.<function>()) prevent row-by-row re-evaluation.
-- Every policy uses DROP POLICY IF EXISTS first to allow idempotent re-running.
-- ==============================================================================
alter table public.mods enable row level security;

alter table public.mod_releases enable row level security;

alter table public.mod_ratings enable row level security;

alter table public.creator_roles enable row level security;

-- --- Creator Roles RLS Policies ---
drop policy if exists "Creator roles are viewable by everyone" on public.creator_roles;

create policy "Creator roles are viewable by everyone" on public.creator_roles for
select
  using (true);

-- Seed initial core developer account
insert into
  public.creator_roles (handle, role, email, description)
values
  (
    'Meta-Dusk',
    'developer',
    'andredcxxv@gmail.com',
    'Core Developer & Author'
  )
on conflict (handle) do update
set role = excluded.role,
email = excluded.email;

-- --- Mods RLS Policies ---
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

drop policy if exists "Creators can update their own mods" on public.mods;

create policy "Creators can update their own mods" on public.mods
for update
  using (
    (
      select
        auth.uid ()
    ) = author_id
  );

drop policy if exists "Creators can delete their own mods" on public.mods;

create policy "Creators can delete their own mods" on public.mods for delete using (
  (
    select
      auth.uid ()
  ) = author_id
);

-- --- Releases RLS Policies ---
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

-- --- Ratings RLS Policies ---
drop policy if exists "Ratings are viewable by everyone" on public.mod_ratings;

create policy "Ratings are viewable by everyone" on public.mod_ratings for
select
  using (true);

-- Drop old legacy policy if present
drop policy if exists "Authenticated users can submit or update their ratings" on public.mod_ratings;

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
-- STORAGE BUCKET FOR MOD ZIP PACKAGES
-- ==============================================================================
insert into
  storage.buckets (id, name, public)
values
  ('mods', 'mods', true)
on conflict (id) do nothing;

-- Security Advisor: Public buckets do not need a broad SELECT policy on storage.objects
-- (Public CDN URLs serve objects directly; dropping broad SELECT prevents scraping/listing).
drop policy if exists "Mod packages are publicly downloadable" on storage.objects;

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