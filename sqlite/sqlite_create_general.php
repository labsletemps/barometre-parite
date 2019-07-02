<?php
try{
    $pdo = new PDO('sqlite:'.dirname(__FILE__).'/YOUR-DATABASE-NAME.sqlite');
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    $pdo->query(<<<EOF
    CREATE TABLE IF NOT EXISTS opinions (
    id         INTEGER         PRIMARY KEY AUTOINCREMENT,
    titre      VARCHAR( 250 ),
    pubdate    DATETIME,
    author     VARCHAR (100),
    male       INTEGER,
    female     INTEGER,
    unknown    INTEGER
);
EOF
);

} catch(Exception $e) {
    echo "Erreur d’accès à la bdd: ".$e->getMessage();
    die();
}
