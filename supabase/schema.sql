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
    tags text [] not null default '{}',
    is_pack boolean not null default false,
    contained_entities text [] not null default '{}',
    config_version integer not null default 10,
    target_app_version text not null default '0.8.0',
    package_url text,
    icon_url text,
    downloads integer not null default 0,
    size_bytes bigint not null default 0,
    created_at timestamp
    with
        time zone not null default now (),
        updated_at timestamp
    with
        time zone not null default now ()
);

-- MOD RELEASES TABLE (Git-like version history)
create table if not exists public.mod_releases (
    id uuid primary key default gen_random_uuid (),
    mod_id text not null references public.mods (id) on delete cascade,
    version text not null,
    changelog text not null default '',
    download_url text,
    size_bytes bigint not null default 0,
    config_version integer not null default 10,
    target_app_version text not null default '0.8.0',
    created_at timestamp
    with
        time zone not null default now (),
        unique (mod_id, version)
);

-- MOD RATINGS TABLE (1.0 to 10.0 per user per mod)
create table if not exists public.mod_ratings (
    mod_id text not null references public.mods (id) on delete cascade,
    user_id uuid not null references auth.users (id) on delete cascade,
    rating numeric(3, 1) not null check (
        rating >= 1.0
        and rating <= 10.0
    ),
    created_at timestamp
    with
        time zone not null default now (),
        primary key (mod_id, user_id)
);

-- ENABLE ROW LEVEL SECURITY (RLS)
alter table public.mods enable row level security;

alter table public.mod_releases enable row level security;

alter table public.mod_ratings enable row level security;

-- Mods RLS Policies
create policy "Mods are viewable by everyone" on public.mods for
select
    using (true);

create policy "Authenticated creators can publish mods" on public.mods for insert
with
    check (auth.role () = 'authenticated');

create policy "Creators can update their own mods" on public.mods for
update using (auth.uid () = author_id);

-- Releases RLS Policies
create policy "Releases are viewable by everyone" on public.mod_releases for
select
    using (true);

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
                    author_id = auth.uid ()
                    or author_id is null
                )
        )
    );

-- Ratings RLS Policies
create policy "Ratings are viewable by everyone" on public.mod_ratings for
select
    using (true);

create policy "Authenticated users can submit or update their ratings" on public.mod_ratings for all using (auth.uid () = user_id)
with
    check (auth.uid () = user_id);

-- STORAGE BUCKET FOR MOD ZIP PACKAGES
insert into
    storage.buckets (id, name, public)
values
    ('mods', 'mods', true)
on conflict (id) do nothing;

create policy "Mod packages are publicly downloadable" on storage.objects for
select
    using (bucket_id = 'mods');

create policy "Authenticated creators can upload mod packages" on storage.objects for insert
with
    check (
        bucket_id = 'mods'
        and auth.role () = 'authenticated'
    );

create policy "Creators can update mod packages" on storage.objects for
update using (
    bucket_id = 'mods'
    and auth.role () = 'authenticated'
);

-- EXPLICIT API GRANTS
-- (Required because "Automatically expose new tables" is disabled)
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

-- Sequences / uuid generators if needed
grant usage,
select
    on all sequences in schema public to anon,
    authenticated;

-- MISSING DELETE POLICIES
-- (Allows authors to unpublish/delete mods & releases)
create policy "Creators can delete their own mods" on public.mods for delete using (auth.uid () = author_id);

create policy "Creators can delete releases of their own mods" on public.mod_releases for delete using (
    exists (
        select
            1
        from
            public.mods
        where
            id = mod_releases.mod_id
            and author_id = auth.uid ()
    )
);

create policy "Creators can delete mod packages" on storage.objects for delete using (
    bucket_id = 'mods'
    and auth.role () = 'authenticated'
);

-- ==============================================================================
-- SECURITY HARDENING
-- ==============================================================================
-- Revoke PostgREST RPC execution privileges on internal SECURITY DEFINER functions
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