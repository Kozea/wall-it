drop table if exists postit;
drop table if exists color;

create table postit(
    post_id integer primary key autoincrement,
    owner text not null,
    text text not null,
    date text not null,
    x integer,
    y integer
);

create table color(
    code_color text,
    owner text primary key
);
