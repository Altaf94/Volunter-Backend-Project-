--
-- PostgreSQL database dump
--

\restrict uIRAiZ0hPPuMJm2EyY10yCggk3GnGPcQEZQnY2D65UozLFb98Cz75DxhtxEy7pc

-- Dumped from database version 14.20 (Homebrew)
-- Dumped by pg_dump version 14.20 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: batch_status; Type: TYPE; Schema: public; Owner: altafhassan
--

CREATE TYPE public.batch_status AS ENUM (
    'processing',
    'validated',
    'submitted',
    'approved',
    'completed',
    'failed'
);


ALTER TYPE public.batch_status OWNER TO altafhassan;

--
-- Name: dispatch_status; Type: TYPE; Schema: public; Owner: altafhassan
--

CREATE TYPE public.dispatch_status AS ENUM (
    'preparing',
    'ready',
    'dispatched',
    'received'
);


ALTER TYPE public.dispatch_status OWNER TO altafhassan;

--
-- Name: kit_status; Type: TYPE; Schema: public; Owner: altafhassan
--

CREATE TYPE public.kit_status AS ENUM (
    'not_prepared',
    'preparing',
    'prepared',
    'dispatched',
    'received'
);


ALTER TYPE public.kit_status OWNER TO altafhassan;

--
-- Name: print_status; Type: TYPE; Schema: public; Owner: altafhassan
--

CREATE TYPE public.print_status AS ENUM (
    'not_printed',
    'printing',
    'printed',
    'dispatched'
);


ALTER TYPE public.print_status OWNER TO altafhassan;

--
-- Name: volunteer_status; Type: TYPE; Schema: public; Owner: altafhassan
--

CREATE TYPE public.volunteer_status AS ENUM (
    'pending',
    'ok',
    'rejected',
    'discrepant_same_event',
    'discrepant_multiple_events',
    'submitted',
    'approved',
    'printed',
    'dispatched'
);


ALTER TYPE public.volunteer_status OWNER TO altafhassan;

--
-- Name: generate_volunteer_id(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.generate_volunteer_id() RETURNS character varying
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN 'VID-' || UPPER(SUBSTRING(MD5(RANDOM()::TEXT) FROM 1 FOR 6));
END;
$$;


ALTER FUNCTION public.generate_volunteer_id() OWNER TO postgres;

--
-- Name: update_batch_counts(); Type: FUNCTION; Schema: public; Owner: altafhassan
--

CREATE FUNCTION public.update_batch_counts() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE upload_batches 
    SET 
        valid_records = (SELECT COUNT(*) FROM volunteers WHERE upload_batch_id = NEW.upload_batch_id AND status = 'ok'),
        rejected_records = (SELECT COUNT(*) FROM volunteers WHERE upload_batch_id = NEW.upload_batch_id AND status = 'rejected'),
        discrepant_records = (SELECT COUNT(*) FROM volunteers WHERE upload_batch_id = NEW.upload_batch_id AND status IN ('discrepant_same_event', 'discrepant_multiple_events')),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.upload_batch_id;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_batch_counts() OWNER TO altafhassan;

--
-- Name: update_position_quota_count(); Type: FUNCTION; Schema: public; Owner: altafhassan
--

CREATE FUNCTION public.update_position_quota_count() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- When volunteer becomes approved/printed/dispatched, increment filled_count
    IF NEW.status IN ('approved', 'printed', 'dispatched') AND 
       (OLD.status IS NULL OR OLD.status NOT IN ('approved', 'printed', 'dispatched')) THEN
        UPDATE event_position_quotas 
        SET filled_count = filled_count + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE event_id = NEW.event_id 
          AND access_level_id = NEW.access_level_id 
          AND duty_type_id = NEW.duty_type_id;
    END IF;
    
    -- When volunteer status changes from approved to rejected, decrement filled_count
    IF NEW.status = 'rejected' AND OLD.status IN ('approved', 'printed', 'dispatched') THEN
        UPDATE event_position_quotas 
        SET filled_count = GREATEST(0, filled_count - 1),
            updated_at = CURRENT_TIMESTAMP
        WHERE event_id = NEW.event_id 
          AND access_level_id = NEW.access_level_id 
          AND duty_type_id = NEW.duty_type_id;
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_position_quota_count() OWNER TO altafhassan;

--
-- Name: update_updated_at(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at() OWNER TO postgres;

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: altafhassan
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO altafhassan;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: access_level_duty_types; Type: TABLE; Schema: public; Owner: altafhassan
--

CREATE TABLE public.access_level_duty_types (
    id integer NOT NULL,
    access_level_id integer NOT NULL,
    duty_type_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.access_level_duty_types OWNER TO altafhassan;

--
-- Name: access_level_duty_types_id_seq; Type: SEQUENCE; Schema: public; Owner: altafhassan
--

CREATE SEQUENCE public.access_level_duty_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.access_level_duty_types_id_seq OWNER TO altafhassan;

--
-- Name: access_level_duty_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altafhassan
--

ALTER SEQUENCE public.access_level_duty_types_id_seq OWNED BY public.access_level_duty_types.id;


--
-- Name: access_levels; Type: TABLE; Schema: public; Owner: altafhassan
--

CREATE TABLE public.access_levels (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.access_levels OWNER TO altafhassan;

--
-- Name: access_levels_id_seq; Type: SEQUENCE; Schema: public; Owner: altafhassan
--

CREATE SEQUENCE public.access_levels_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.access_levels_id_seq OWNER TO altafhassan;

--
-- Name: access_levels_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altafhassan
--

ALTER SEQUENCE public.access_levels_id_seq OWNED BY public.access_levels.id;


--
-- Name: band_type_access_level_duty_type; Type: TABLE; Schema: public; Owner: altafhassan
--

CREATE TABLE public.band_type_access_level_duty_type (
    id integer NOT NULL,
    band_type_id integer NOT NULL,
    access_level_id integer NOT NULL,
    duty_type_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.band_type_access_level_duty_type OWNER TO altafhassan;

--
-- Name: band_type_access_level_duty_type_id_seq; Type: SEQUENCE; Schema: public; Owner: altafhassan
--

CREATE SEQUENCE public.band_type_access_level_duty_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.band_type_access_level_duty_type_id_seq OWNER TO altafhassan;

--
-- Name: band_type_access_level_duty_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altafhassan
--

ALTER SEQUENCE public.band_type_access_level_duty_type_id_seq OWNED BY public.band_type_access_level_duty_type.id;


--
-- Name: band_types; Type: TABLE; Schema: public; Owner: altafhassan
--

CREATE TABLE public.band_types (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.band_types OWNER TO altafhassan;

--
-- Name: band_types_id_seq; Type: SEQUENCE; Schema: public; Owner: altafhassan
--

CREATE SEQUENCE public.band_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.band_types_id_seq OWNER TO altafhassan;

--
-- Name: band_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altafhassan
--

ALTER SEQUENCE public.band_types_id_seq OWNED BY public.band_types.id;


--
-- Name: duty_types; Type: TABLE; Schema: public; Owner: altafhassan
--

CREATE TABLE public.duty_types (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.duty_types OWNER TO altafhassan;

--
-- Name: duty_types_id_seq; Type: SEQUENCE; Schema: public; Owner: altafhassan
--

CREATE SEQUENCE public.duty_types_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.duty_types_id_seq OWNER TO altafhassan;

--
-- Name: duty_types_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altafhassan
--

ALTER SEQUENCE public.duty_types_id_seq OWNED BY public.duty_types.id;


--
-- Name: error_codes; Type: TABLE; Schema: public; Owner: altafhassan
--

CREATE TABLE public.error_codes (
    id integer NOT NULL,
    code character varying(50) NOT NULL,
    http_status integer,
    severity character varying(20) DEFAULT 'error'::character varying NOT NULL,
    message character varying(255) NOT NULL,
    details text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.error_codes OWNER TO altafhassan;

--
-- Name: error_codes_id_seq; Type: SEQUENCE; Schema: public; Owner: altafhassan
--

CREATE SEQUENCE public.error_codes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.error_codes_id_seq OWNER TO altafhassan;

--
-- Name: error_codes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altafhassan
--

ALTER SEQUENCE public.error_codes_id_seq OWNED BY public.error_codes.id;


--
-- Name: event_access_level_duty_requirements; Type: TABLE; Schema: public; Owner: altafhassan
--

CREATE TABLE public.event_access_level_duty_requirements (
    id integer NOT NULL,
    event_id integer NOT NULL,
    access_level_id integer NOT NULL,
    duty_type_id integer NOT NULL,
    required_count integer DEFAULT 0 NOT NULL,
    remaining integer DEFAULT 0 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT event_access_level_duty_requirements_remaining_check CHECK ((remaining >= 0)),
    CONSTRAINT event_access_level_duty_requirements_required_count_check CHECK ((required_count >= 0))
);


ALTER TABLE public.event_access_level_duty_requirements OWNER TO altafhassan;

--
-- Name: event_access_level_duty_requirements_id_seq; Type: SEQUENCE; Schema: public; Owner: altafhassan
--

CREATE SEQUENCE public.event_access_level_duty_requirements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.event_access_level_duty_requirements_id_seq OWNER TO altafhassan;

--
-- Name: event_access_level_duty_requirements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altafhassan
--

ALTER SEQUENCE public.event_access_level_duty_requirements_id_seq OWNED BY public.event_access_level_duty_requirements.id;


--
-- Name: events; Type: TABLE; Schema: public; Owner: altafhassan
--

CREATE TABLE public.events (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.events OWNER TO altafhassan;

--
-- Name: events_id_seq; Type: SEQUENCE; Schema: public; Owner: altafhassan
--

CREATE SEQUENCE public.events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.events_id_seq OWNER TO altafhassan;

--
-- Name: events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altafhassan
--

ALTER SEQUENCE public.events_id_seq OWNED BY public.events.id;


--
-- Name: roles; Type: TABLE; Schema: public; Owner: altafhassan
--

CREATE TABLE public.roles (
    id integer NOT NULL,
    scope character varying(20) NOT NULL,
    name character varying(100) NOT NULL,
    can_view boolean DEFAULT false NOT NULL,
    can_make boolean DEFAULT false NOT NULL,
    can_check boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT roles_scope_check CHECK (((scope)::text = ANY ((ARRAY['national'::character varying, 'regional'::character varying])::text[])))
);


ALTER TABLE public.roles OWNER TO altafhassan;

--
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: altafhassan
--

CREATE SEQUENCE public.roles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.roles_id_seq OWNER TO altafhassan;

--
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altafhassan
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: altafhassan
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    full_name character varying(200) NOT NULL,
    role_id integer,
    scope character varying(20),
    region_id integer,
    is_active boolean DEFAULT true NOT NULL,
    last_login timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT users_scope_check CHECK (((scope)::text = ANY ((ARRAY['national'::character varying, 'regional'::character varying])::text[])))
);


ALTER TABLE public.users OWNER TO altafhassan;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: altafhassan
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO altafhassan;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: altafhassan
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: access_level_duty_types id; Type: DEFAULT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.access_level_duty_types ALTER COLUMN id SET DEFAULT nextval('public.access_level_duty_types_id_seq'::regclass);


--
-- Name: access_levels id; Type: DEFAULT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.access_levels ALTER COLUMN id SET DEFAULT nextval('public.access_levels_id_seq'::regclass);


--
-- Name: band_type_access_level_duty_type id; Type: DEFAULT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.band_type_access_level_duty_type ALTER COLUMN id SET DEFAULT nextval('public.band_type_access_level_duty_type_id_seq'::regclass);


--
-- Name: band_types id; Type: DEFAULT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.band_types ALTER COLUMN id SET DEFAULT nextval('public.band_types_id_seq'::regclass);


--
-- Name: duty_types id; Type: DEFAULT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.duty_types ALTER COLUMN id SET DEFAULT nextval('public.duty_types_id_seq'::regclass);


--
-- Name: error_codes id; Type: DEFAULT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.error_codes ALTER COLUMN id SET DEFAULT nextval('public.error_codes_id_seq'::regclass);


--
-- Name: event_access_level_duty_requirements id; Type: DEFAULT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.event_access_level_duty_requirements ALTER COLUMN id SET DEFAULT nextval('public.event_access_level_duty_requirements_id_seq'::regclass);


--
-- Name: events id; Type: DEFAULT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.events ALTER COLUMN id SET DEFAULT nextval('public.events_id_seq'::regclass);


--
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: access_level_duty_types access_level_duty_types_access_level_id_duty_type_id_key; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.access_level_duty_types
    ADD CONSTRAINT access_level_duty_types_access_level_id_duty_type_id_key UNIQUE (access_level_id, duty_type_id);


--
-- Name: access_level_duty_types access_level_duty_types_pkey; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.access_level_duty_types
    ADD CONSTRAINT access_level_duty_types_pkey PRIMARY KEY (id);


--
-- Name: access_levels access_levels_name_key; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.access_levels
    ADD CONSTRAINT access_levels_name_key UNIQUE (name);


--
-- Name: access_levels access_levels_pkey; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.access_levels
    ADD CONSTRAINT access_levels_pkey PRIMARY KEY (id);


--
-- Name: band_type_access_level_duty_type band_type_access_level_duty_t_band_type_id_access_level_id__key; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.band_type_access_level_duty_type
    ADD CONSTRAINT band_type_access_level_duty_t_band_type_id_access_level_id__key UNIQUE (band_type_id, access_level_id, duty_type_id);


--
-- Name: band_type_access_level_duty_type band_type_access_level_duty_type_pkey; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.band_type_access_level_duty_type
    ADD CONSTRAINT band_type_access_level_duty_type_pkey PRIMARY KEY (id);


--
-- Name: band_types band_types_name_key; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.band_types
    ADD CONSTRAINT band_types_name_key UNIQUE (name);


--
-- Name: band_types band_types_pkey; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.band_types
    ADD CONSTRAINT band_types_pkey PRIMARY KEY (id);


--
-- Name: duty_types duty_types_name_key; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.duty_types
    ADD CONSTRAINT duty_types_name_key UNIQUE (name);


--
-- Name: duty_types duty_types_pkey; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.duty_types
    ADD CONSTRAINT duty_types_pkey PRIMARY KEY (id);


--
-- Name: error_codes error_codes_code_key; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.error_codes
    ADD CONSTRAINT error_codes_code_key UNIQUE (code);


--
-- Name: error_codes error_codes_pkey; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.error_codes
    ADD CONSTRAINT error_codes_pkey PRIMARY KEY (id);


--
-- Name: event_access_level_duty_requirements event_access_level_duty_requi_event_id_access_level_id_duty_key; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.event_access_level_duty_requirements
    ADD CONSTRAINT event_access_level_duty_requi_event_id_access_level_id_duty_key UNIQUE (event_id, access_level_id, duty_type_id);


--
-- Name: event_access_level_duty_requirements event_access_level_duty_requirements_pkey; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.event_access_level_duty_requirements
    ADD CONSTRAINT event_access_level_duty_requirements_pkey PRIMARY KEY (id);


--
-- Name: events events_name_key; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_name_key UNIQUE (name);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- Name: roles roles_scope_name_key; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_scope_name_key UNIQUE (scope, name);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_access_level_duty_types_access_level_id; Type: INDEX; Schema: public; Owner: altafhassan
--

CREATE INDEX idx_access_level_duty_types_access_level_id ON public.access_level_duty_types USING btree (access_level_id);


--
-- Name: idx_access_level_duty_types_duty_type_id; Type: INDEX; Schema: public; Owner: altafhassan
--

CREATE INDEX idx_access_level_duty_types_duty_type_id ON public.access_level_duty_types USING btree (duty_type_id);


--
-- Name: idx_band_type_access_level_duty_type_access_level_id; Type: INDEX; Schema: public; Owner: altafhassan
--

CREATE INDEX idx_band_type_access_level_duty_type_access_level_id ON public.band_type_access_level_duty_type USING btree (access_level_id);


--
-- Name: idx_band_type_access_level_duty_type_band_type_id; Type: INDEX; Schema: public; Owner: altafhassan
--

CREATE INDEX idx_band_type_access_level_duty_type_band_type_id ON public.band_type_access_level_duty_type USING btree (band_type_id);


--
-- Name: idx_band_type_access_level_duty_type_duty_type_id; Type: INDEX; Schema: public; Owner: altafhassan
--

CREATE INDEX idx_band_type_access_level_duty_type_duty_type_id ON public.band_type_access_level_duty_type USING btree (duty_type_id);


--
-- Name: idx_event_access_level_duty_requirements_access_level_id; Type: INDEX; Schema: public; Owner: altafhassan
--

CREATE INDEX idx_event_access_level_duty_requirements_access_level_id ON public.event_access_level_duty_requirements USING btree (access_level_id);


--
-- Name: idx_event_access_level_duty_requirements_duty_type_id; Type: INDEX; Schema: public; Owner: altafhassan
--

CREATE INDEX idx_event_access_level_duty_requirements_duty_type_id ON public.event_access_level_duty_requirements USING btree (duty_type_id);


--
-- Name: idx_event_access_level_duty_requirements_event_id; Type: INDEX; Schema: public; Owner: altafhassan
--

CREATE INDEX idx_event_access_level_duty_requirements_event_id ON public.event_access_level_duty_requirements USING btree (event_id);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: altafhassan
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: idx_users_region_id; Type: INDEX; Schema: public; Owner: altafhassan
--

CREATE INDEX idx_users_region_id ON public.users USING btree (region_id);


--
-- Name: idx_users_role_id; Type: INDEX; Schema: public; Owner: altafhassan
--

CREATE INDEX idx_users_role_id ON public.users USING btree (role_id);


--
-- Name: access_level_duty_types access_level_duty_types_access_level_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.access_level_duty_types
    ADD CONSTRAINT access_level_duty_types_access_level_id_fkey FOREIGN KEY (access_level_id) REFERENCES public.access_levels(id) ON DELETE CASCADE;


--
-- Name: access_level_duty_types access_level_duty_types_duty_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.access_level_duty_types
    ADD CONSTRAINT access_level_duty_types_duty_type_id_fkey FOREIGN KEY (duty_type_id) REFERENCES public.duty_types(id) ON DELETE CASCADE;


--
-- Name: band_type_access_level_duty_type band_type_access_level_duty_type_access_level_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.band_type_access_level_duty_type
    ADD CONSTRAINT band_type_access_level_duty_type_access_level_id_fkey FOREIGN KEY (access_level_id) REFERENCES public.access_levels(id) ON DELETE CASCADE;


--
-- Name: band_type_access_level_duty_type band_type_access_level_duty_type_band_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.band_type_access_level_duty_type
    ADD CONSTRAINT band_type_access_level_duty_type_band_type_id_fkey FOREIGN KEY (band_type_id) REFERENCES public.band_types(id) ON DELETE CASCADE;


--
-- Name: band_type_access_level_duty_type band_type_access_level_duty_type_duty_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.band_type_access_level_duty_type
    ADD CONSTRAINT band_type_access_level_duty_type_duty_type_id_fkey FOREIGN KEY (duty_type_id) REFERENCES public.duty_types(id) ON DELETE CASCADE;


--
-- Name: event_access_level_duty_requirements event_access_level_duty_requirements_access_level_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.event_access_level_duty_requirements
    ADD CONSTRAINT event_access_level_duty_requirements_access_level_id_fkey FOREIGN KEY (access_level_id) REFERENCES public.access_levels(id) ON DELETE CASCADE;


--
-- Name: event_access_level_duty_requirements event_access_level_duty_requirements_duty_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.event_access_level_duty_requirements
    ADD CONSTRAINT event_access_level_duty_requirements_duty_type_id_fkey FOREIGN KEY (duty_type_id) REFERENCES public.duty_types(id) ON DELETE CASCADE;


--
-- Name: event_access_level_duty_requirements event_access_level_duty_requirements_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.event_access_level_duty_requirements
    ADD CONSTRAINT event_access_level_duty_requirements_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(id) ON DELETE CASCADE;


--
-- Name: users users_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: altafhassan
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict uIRAiZ0hPPuMJm2EyY10yCggk3GnGPcQEZQnY2D65UozLFb98Cz75DxhtxEy7pc

