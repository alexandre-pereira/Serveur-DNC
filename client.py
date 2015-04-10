# coding: utf-8
import re
from thread import start_new_thread
from logger import Logger


class Client:

    tous = []
    discussionOuverte = [] # Qui est autorisé à parler avec qui - 0: client, 1: client
    propositionFichiers = [] # TODO : contient ClientEmetteur, ClientRecepteur, Chemin du fichier

    def __init__(self, pconn):

        self.conn = pconn;
        self.nom = None;
        self.actif = True
        self.discussionEnAttente = []
        start_new_thread(self.wait4name, ())

    def initco(self):
        for c in Client.tous:
            c.conn.sendall("302 "+ self.nom)

        Client.tous.append(self)
        self.conn.sendall("200")
        start_new_thread(self.client_thread, ())

    def wait4name(self):
        disconnected = False

        while True:
            try:
                tmpData = self.conn.recv(1024)
            except:
                disconnected = True
                break
            if not tmpData:
                disconnected = True
                break

            data = ' '.join(tmpData.split())
            commande = data.split(" ")[0]
            # todo message de retour + utilisateur existant
            if commande == "/quit": break

            if commande == "/newname":
                name = data[len(commande)+1:]
                if Client.getByName(name) != None:
                    self.conn.sendall("400")
                    continue
                if re.match("^\w{3,15}$", name):
                    self.nom = name
                    self.initco()
                    break
                else: self.conn.sendall("408")
            else: self.conn.sendall("401")
        if disconnected:
            self.conn.close()

    def client_thread(self):

        # ON ECOUTE CHAQUE CLIENT
        while True:
            try:
                tmpData = self.conn.recv(1024)
            except:
                break
            if not tmpData: break
            data = ' '.join(tmpData.split())
            Logger.logger.info(self.nom +" :: " +data)

            if data == "/quit":
                self.conn.sendall("201")
                break

            if data[0] == '/': #c'est une commande spéciale
                reponse = self.getReply(data[1:])
            else: #c'est un message à envoyer à tous les clients actifs
                for c in Client.tous:
                    if c!=self: c.conn.sendall("304 "+ self.nom + " " + data)
                reponse = "202"

            if reponse:
                self.conn.sendall(reponse)


        #EXIT
        Client.tous.remove(self)
        for c in Client.tous:
            c.conn.sendall("303 "+ self.nom)
        self.conn.close()
        # todo: nettoyer listes transfert fichiers + acceptpm


    def getReply(self, data):
        commande = data.split(" ")[0]
        argument = data[len(commande)+1:]
        if(commande == "name"):
            if re.match("^\w{3,15}$", argument):
                if Client.getByName(argument): return "400"
                ancienNom = self.nom
                self.nom = argument
                for c in Client.tous:
                    if c != self:
                        c.conn.sendall("305 "+ancienNom+" "+self.nom)
                return "203 " + self.nom
            return "408"

        if(commande == "pm"):
            dest = Client.getByName(argument.split(" ")[0])
            if dest:
                if not Client.isDiscussionOuverte(dest, self): return "402"
                dest.conn.sendall("306 "+ self.nom + " " + argument[len(dest.nom)+1:])
                return "205"
            return "403"

        if(commande == "askpm"):
            dest = Client.getByName(argument.split(" ")[0])
            if dest:
                d = dest.getDiscussionEnAttenteFrom(self)
                if not d:
                    dest.discussionEnAttente.append(self)
                    dest.conn.sendall("307 " + self.nom)
                    return "206"
                return "404"
            return "403"

        if(commande == "acceptpm"):
            dest = Client.getByName(argument.split(" ")[0])
            # todo les 2 on fait un accept
            if dest:
                d = self.getDiscussionEnAttenteFrom(dest)
                if d:
                    self.discussionEnAttente.remove(dest)
                    Client.discussionOuverte.append([self, dest])
                    d.conn.sendall("308 " + self.nom)
                    return "207"
                return "405"
            return "403"

        if(commande == "rejectpm"):
            dest = Client.getByName(argument.split(" ")[0])
            if dest:
                d = self.getDiscussionEnAttenteFrom(dest)
                if d:
                    self.discussionEnAttente.remove(dest)
                    # todo arreter une connexion deja ouverte
                    d.conn.sendall("309" + self.nom)
                    return "208"
                return "405"
            return "403"

        if(commande == "enable"):
            self.actif = True
            for c in Client.tous:
                if c != self:
                    c.conn.sendall("310 "+self.nom)
            return "209"

        if(commande == "disable"):
            self.actif = False
            for c in Client.tous:
                if c != self:
                    c.conn.sendall("311 "+self.nom)
            return "210"

        if(commande == "pmfile"):

            arguments = argument.split(" ")
            dest = Client.getByName(arguments[0])
            path = argument[len(arguments[0])+1:]
            # todo FACULTATIF : already proposed this file
            if dest and path:
                Client.propositionFichiers.append([self, dest, path])
                dest.conn.sendall("312 "+self.nom + " "+path)
                return "211"
            return "403"

        if(commande == "acceptfile"):
            arguments = argument.split(" ")
            dest = Client.getByName(arguments[0])
            port = arguments[1]
            path = argument[len(arguments[0])+len(arguments[1])+2:]
            l=[dest, self, path]
            if l in Client.propositionFichiers and port:
                Client.propositionFichiers.remove(l)
                if port:
                    ip = self.conn.getpeername()[0]
                    dest.conn.sendall("313 "+dest.nom+" "+port+" "+ip+" "+path)
                    return "212"
                else: return "407"
            return "406"

        if(commande == "rejectfile"):
            arguments = argument.split(" ")
            dest = Client.getByName(arguments[0])
            path = argument[len(arguments[0])+len(arguments[1])+2:]
            l=[dest, self, path]
            if l in Client.propositionFichiers:
                Client.propositionFichiers.remove(l)
                dest.conn.sendall("314 "+dest.nom+" "+path)
                return "213"
            return "406"

        if(commande == "userlistaway"):
            clientListAway = ""
            for c in Client.tous:
                if not c.actif:
                    clientListAway += " " + c.nom
            self.conn.sendall("301" + clientListAway)

        if(commande == "userlist"):
            clientList = ""
            for c in Client.tous:
                if c.actif:
                    clientList += " " + c.nom
            self.conn.sendall("300" + clientList)



        return "407"

    @staticmethod
    def getByName(nom):
        for c in Client.tous:
            if c.nom == nom: return c
        return None

    def getProposedFile(self, emet, path):
        for p in Client.propositionFichiers:
            if p[0] == emet and p[1] == self and p[2] == path:
                return p
        return None

    @staticmethod
    def isDiscussionOuverte(c1, c2):
        for ac in Client.discussionOuverte:
            if (ac[0] == c1 and ac[1] == c2) or (ac[1] == c1 and ac[0] == c2) :
                return True
        return False


    def getDiscussionEnAttenteFrom(self, c1):
        for ac in self.discussionEnAttente:
            if (ac == c1):
                return ac
        return None