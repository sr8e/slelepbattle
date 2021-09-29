create table sleeptime(
  id serial not null primary key,
  uid bigint not null,
  post_id bigint not null,
  sleeptime timestamp with time zone not null
);

create table waketime(
  id serial not null primary key,
  uid bigint not null,
  post_id bigint not null,
  waketime timestamp with time zone not null
);

create table score(
  id serial not null primary key,
  uid bigint not null,
  sleep_pk integer references sleeptime (id) not null,
  wake_pk integer references waketime (id) not null,
  score numeric not null,
  date date not null,
  owner bigint not null,
  unique (uid, date)
);

create table attack(
  uid bigint not null primary key,
  state integer not null,
  target bigint,
  attack_date date,
  swap_date date,
  confirmed_at timestamp with time zone
);
