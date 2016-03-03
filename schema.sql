drop table if exists postit;
drop table if exists color;
drop table if exists credentials;

create table postit(
    post_id integer primary key autoincrement,
    owner text not null,
    text text not null,
    x integer,
    y integer
);

create table color(
    code_color text,
    owner text primary key
);

create table credentials(
    user text primary key not null,
    credentials_content text not null
);
